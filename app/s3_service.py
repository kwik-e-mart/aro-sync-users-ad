import hashlib
import json
from typing import Optional, Tuple
import boto3
from botocore.exceptions import ClientError
from .config import Config
from .models import SyncResult


class S3Service:
    def __init__(self, config: Config):
        self.config = config

        # Configure S3 client with optional endpoint URL for LocalStack
        client_config = {
            'region_name': config.aws_region
        }

        if config.aws_endpoint_url:
            client_config['endpoint_url'] = config.aws_endpoint_url

        self.s3_client = boto3.client('s3', **client_config)

    def _calculate_md5(self, ad_users_content: bytes, mapping_content: bytes) -> str:
        """Calculate MD5 hash of both input files combined."""
        combined = ad_users_content + mapping_content
        return hashlib.md5(combined).hexdigest()

    def fetch_input_files(self) -> Tuple[bytes, bytes]:
        """
        Fetch AD users and mapping files from S3.

        Returns:
            Tuple of (ad_users_content, mapping_content)
        """
        try:
            # Fetch AD users file
            ad_users_response = self.s3_client.get_object(
                Bucket=self.config.s3_bucket,
                Key=self.config.s3_ad_users_file
            )
            ad_users_content = ad_users_response['Body'].read()

            # Fetch mapping file
            mapping_response = self.s3_client.get_object(
                Bucket=self.config.s3_bucket,
                Key=self.config.s3_mapping_file
            )
            mapping_content = mapping_response['Body'].read()

            return ad_users_content, mapping_content

        except ClientError as e:
            raise Exception(f"S3 ClientError: {str(e)}, Bucket: {self.config.s3_bucket}, Region: {self.config.aws_region}, Endpoint: {self.config.aws_endpoint_url}")
        except Exception as e:
            raise Exception(f"Error fetching files from S3: {str(e)}, Bucket: {self.config.s3_bucket}, Region: {self.config.aws_region}, Endpoint: {self.config.aws_endpoint_url}")

    def check_existing_result(self, md5_hash: str) -> Optional[SyncResult]:
        """
        Check if a result file already exists for this MD5 hash.

        Args:
            md5_hash: MD5 hash of the input files

        Returns:
            SyncResult if exists, None otherwise
        """
        result_key = f"{self.config.s3_results_prefix}{md5_hash}.json"

        try:
            response = self.s3_client.get_object(
                Bucket=self.config.s3_bucket,
                Key=result_key
            )
            result_data = json.loads(response['Body'].read())
            return SyncResult(**result_data)

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise Exception(f"Error checking existing result: {str(e)}")

    def store_result(self, md5_hash: str, result: SyncResult) -> str:
        """
        Store sync result in S3.

        Args:
            md5_hash: MD5 hash of the input files
            result: The sync result to store

        Returns:
            S3 key where the result was stored
        """
        result_key = f"{self.config.s3_results_prefix}{md5_hash}.json"

        try:
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=result_key,
                Body=result.model_dump_json(indent=2),
                ContentType='application/json'
            )
            return result_key

        except ClientError as e:
            raise Exception(f"Error storing result to S3: {str(e)}")

    def get_file_md5(self, ad_users_content: bytes, mapping_content: bytes) -> str:
        """
        Calculate MD5 hash for the given file contents.

        Args:
            ad_users_content: AD users file content
            mapping_content: Mapping file content

        Returns:
            MD5 hash string
        """
        return self._calculate_md5(ad_users_content, mapping_content)

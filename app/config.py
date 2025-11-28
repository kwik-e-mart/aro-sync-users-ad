from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    nullplatform_api_key: str
    organization_id: int
    auth_api_url: str = "https://auth.nullplatform.io"
    users_api_url: str = "https://users.nullplatform.io"

    # S3 Configuration
    s3_bucket: str
    s3_ad_users_file: str
    s3_mapping_file: str
    s3_results_prefix: str = "results/"
    aws_region: str = "us-east-1"
    aws_endpoint_url: Optional[str] = None  # For LocalStack support


config = Config()

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from .models import SyncResult
from .repositories import UserRepository, AuthzRepository
from .services import SyncService
from .s3_service import S3Service
from .config import config
from .client import NullplatformClient
from .auth import verify_api_key

app = FastAPI(title="AD User Sync API")

# Initialize Nullplatform client
nullplatform_client = NullplatformClient(config)

# Dependency Injection
user_repo = UserRepository(nullplatform_client)
authz_repo = AuthzRepository(nullplatform_client)
sync_service = SyncService(user_repo, authz_repo)
s3_service = S3Service(config)

@app.post("/sync", response_model=SyncResult)
async def sync_users(
    ad_users_file: UploadFile = File(...),
    mapping_file: UploadFile = File(...),
    dry_run: bool = False,
    force: bool = False,
    api_key: str = Depends(verify_api_key)
):
    """
    Sync users from uploaded CSV files.

    Args:
        ad_users_file: AD users CSV file
        mapping_file: Group mapping CSV file
        dry_run: If True, only simulate changes without applying them
        force: If True, force sync even if result already exists
    """
    try:
        ad_content = await ad_users_file.read()
        mapping_content = await mapping_file.read()

        result = sync_service.execute_sync(
            ad_content,
            mapping_content,
            dry_run=dry_run,
            force=force
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync-from-s3", response_model=SyncResult)
async def sync_users_from_s3(
    dry_run: bool = False,
    force: bool = False,
    api_key: str = Depends(verify_api_key)
):
    """
    Sync users from CSV files stored in S3.

    The files are fetched from S3 using configuration from environment variables.
    Results are cached based on MD5 hash of input files.

    Args:
        dry_run: If True, only simulate changes without applying them
        force: If True, force sync even if result already exists (skip cache check)

    Returns:
        SyncResult with details of the synchronization
    """
    try:
        # Fetch files from S3
        ad_content, mapping_content = s3_service.fetch_input_files()

        # Calculate MD5 hash of input files
        md5_hash = s3_service.get_file_md5(ad_content, mapping_content)

        # Check if result already exists (unless force=True)
        if not force:
            existing_result = s3_service.check_existing_result(md5_hash)
            if existing_result:
                return {
                    **existing_result.model_dump(),
                    "status": "cached",
                    "logs": [
                        f"Result already exists for MD5: {md5_hash}",
                        "Skipping synchronization. Use force=true to re-run.",
                        *existing_result.logs
                    ]
                }

        # Execute sync
        result = sync_service.execute_sync(
            ad_content,
            mapping_content,
            dry_run=dry_run,
            force=force
        )

        # Store result in S3 (only if not dry_run)
        if not dry_run:
            result_key = s3_service.store_result(md5_hash, result)
            result.logs.append(f"Result stored in S3: s3://{config.s3_bucket}/{result_key}")
            result.logs.append(f"MD5 hash: {md5_hash}")

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "AD User Sync API is running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

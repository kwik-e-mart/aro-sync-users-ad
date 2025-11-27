from fastapi import FastAPI, UploadFile, File, HTTPException
from .models import SyncResult
from .repositories import UserRepository, AuthzRepository
from .services import SyncService
from .config import config
from .client import NullplatformClient

app = FastAPI(title="AD User Sync API")

# Initialize Nullplatform client
nullplatform_client = NullplatformClient(config)

# Dependency Injection
user_repo = UserRepository(nullplatform_client)
authz_repo = AuthzRepository(nullplatform_client)
sync_service = SyncService(user_repo, authz_repo)

@app.post("/sync", response_model=SyncResult)
async def sync_users(
    ad_users_file: UploadFile = File(...),
    mapping_file: UploadFile = File(...),
    dry_run: bool = False,
    force: bool = False
):
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

@app.get("/")
def read_root():
    return {"message": "AD User Sync API is running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

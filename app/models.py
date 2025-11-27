from pydantic import BaseModel
from typing import List, Optional

# Models for CSV Data
class ADUserCSV(BaseModel):
    nombre: str
    correo: str
    grupo: str

class GroupMappingCSV(BaseModel):
    grupo: str
    nrn: str
    roles: str  # Comma separated roles in CSV likely

# Internal Models
class User(BaseModel):
    id: str
    username: str
    email: str
    roles: List[str] = []

# API Models
class SyncResult(BaseModel):
    status: str
    users_processed: int
    users_created: int
    users_deleted: int
    users_updated: int
    logs: List[str]

# Nullplatform API Response Models
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_expires_at: int
    organization_id: int
    account_id: int

class NullplatformUser(BaseModel):
    id: int
    email: str
    status: str
    first_name: str
    last_name: str
    organization_id: int
    avatar: Optional[str] = None
    type: str
    provider: str

class PagingInfo(BaseModel):
    offset: int
    limit: int

class UserListResponse(BaseModel):
    paging: PagingInfo
    results: List[NullplatformUser]

class Role(BaseModel):
    id: int
    name: str
    slug: str
    level: Optional[str] = None
    description: str
    can_assign_roles: List[str] = []

class Grant(BaseModel):
    id: int
    nrn: str
    role: Role

class GrantResponse(BaseModel):
    user_id: int
    grants: List[Grant]

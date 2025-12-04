"""
SCIM 2.0 API Router
Implements SCIM endpoints according to RFC 7644
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Header
from typing import Optional
from .scim_models import (
    ScimUser, ScimGroup, ScimListResponse, ScimError,
    ScimPatchRequest, ServiceProviderConfig, ScimResourceType,
    ScimMeta
)
from .scim_service import ScimService
from .auth import verify_api_key

router = APIRouter(prefix="/scim/v2", tags=["SCIM 2.0"])


def get_scim_service(request: Request) -> ScimService:
    """Dependency to get SCIM service from app state"""
    return request.app.state.scim_service


# ServiceProviderConfig endpoint
@router.get("/ServiceProviderConfig", response_model=ServiceProviderConfig)
async def get_service_provider_config():
    """
    Get Service Provider Configuration
    RFC 7644 Section 4
    """
    return ServiceProviderConfig()


# ResourceTypes endpoint
@router.get("/ResourceTypes", response_model=list)
async def get_resource_types():
    """
    Get Resource Types
    RFC 7644 Section 4
    """
    return [
        ScimResourceType(
            id="User",
            name="User",
            endpoint="/scim/v2/Users",
            description="User Account",
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            meta=ScimMeta(
                resourceType="ResourceType",
                location="/scim/v2/ResourceTypes/User"
            )
        ),
        ScimResourceType(
            id="Group",
            name="Group",
            endpoint="/scim/v2/Groups",
            description="Group",
            schema="urn:ietf:params:scim:schemas:core:2.0:Group",
            meta=ScimMeta(
                resourceType="ResourceType",
                location="/scim/v2/ResourceTypes/Group"
            )
        )
    ]


@router.get("/ResourceTypes/{resource_type_id}", response_model=ScimResourceType)
async def get_resource_type(resource_type_id: str):
    """Get a specific resource type"""
    if resource_type_id == "User":
        return ScimResourceType(
            id="User",
            name="User",
            endpoint="/scim/v2/Users",
            description="User Account",
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            meta=ScimMeta(
                resourceType="ResourceType",
                location="/scim/v2/ResourceTypes/User"
            )
        )
    elif resource_type_id == "Group":
        return ScimResourceType(
            id="Group",
            name="Group",
            endpoint="/scim/v2/Groups",
            description="Group",
            schema="urn:ietf:params:scim:schemas:core:2.0:Group",
            meta=ScimMeta(
                resourceType="ResourceType",
                location="/scim/v2/ResourceTypes/Group"
            )
        )
    else:
        raise HTTPException(status_code=404, detail=f"ResourceType {resource_type_id} not found")


# Users endpoints
@router.get("/Users", response_model=ScimListResponse)
async def list_users(
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=1, le=200),
    filter: Optional[str] = Query(None),
    scim_service: ScimService = Depends(get_scim_service),
    api_key: str = Depends(verify_api_key)
):
    """
    List Users
    RFC 7644 Section 3.4.2
    Supports filtering: filter=userName eq "user@example.com"
    """
    try:
        return scim_service.list_users(
            start_index=startIndex,
            count=count,
            filter_expr=filter
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/Users/{user_id}", response_model=ScimUser)
async def get_user(
    user_id: str,
    scim_service: ScimService = Depends(get_scim_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Get User by ID
    RFC 7644 Section 3.4.1
    """
    user = scim_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=ScimError(
                status="404",
                detail=f"User {user_id} not found"
            ).model_dump()
        )
    return user


@router.post("/Users", response_model=ScimUser, status_code=201)
async def create_user(
    user: ScimUser,
    scim_service: ScimService = Depends(get_scim_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Create User
    RFC 7644 Section 3.3
    """
    try:
        # Check if user already exists
        existing_user = scim_service.get_user_by_username(user.userName)
        if existing_user:
            raise HTTPException(
                status_code=409,
                detail=ScimError(
                    status="409",
                    scimType="uniqueness",
                    detail=f"User with userName {user.userName} already exists"
                ).model_dump()
            )

        created_user = scim_service.create_user(user)
        return created_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/Users/{user_id}", response_model=ScimUser)
async def update_user(
    user_id: str,
    user: ScimUser,
    scim_service: ScimService = Depends(get_scim_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Update User (Full Replacement)
    RFC 7644 Section 3.5.1
    """
    try:
        updated_user = scim_service.update_user(user_id, user)
        if not updated_user:
            raise HTTPException(
                status_code=404,
                detail=ScimError(
                    status="404",
                    detail=f"User {user_id} not found"
                ).model_dump()
            )
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/Users/{user_id}", response_model=ScimUser)
async def patch_user(
    user_id: str,
    patch_request: ScimPatchRequest,
    scim_service: ScimService = Depends(get_scim_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Patch User (Partial Update)
    RFC 7644 Section 3.5.2
    """
    try:
        patched_user = scim_service.patch_user(
            user_id,
            [op.model_dump() for op in patch_request.Operations]
        )
        if not patched_user:
            raise HTTPException(
                status_code=404,
                detail=ScimError(
                    status="404",
                    detail=f"User {user_id} not found"
                ).model_dump()
            )
        return patched_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/Users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    scim_service: ScimService = Depends(get_scim_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Delete User
    RFC 7644 Section 3.6
    """
    success = scim_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=ScimError(
                status="404",
                detail=f"User {user_id} not found"
            ).model_dump()
        )
    return None


# Groups endpoints
@router.get("/Groups", response_model=ScimListResponse)
async def list_groups(
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=1, le=200),
    filter: Optional[str] = Query(None),
    scim_service: ScimService = Depends(get_scim_service),
    api_key: str = Depends(verify_api_key)
):
    """
    List Groups
    RFC 7644 Section 3.4.2
    """
    try:
        return scim_service.list_groups(
            start_index=startIndex,
            count=count,
            filter_expr=filter
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/Groups/{group_id}", response_model=ScimGroup)
async def get_group(
    group_id: str,
    scim_service: ScimService = Depends(get_scim_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Get Group by ID
    RFC 7644 Section 3.4.1
    """
    group = scim_service.get_group(group_id)
    if not group:
        raise HTTPException(
            status_code=404,
            detail=ScimError(
                status="404",
                detail=f"Group {group_id} not found"
            ).model_dump()
        )
    return group


@router.put("/Groups/{group_id}", response_model=ScimGroup)
async def update_group(
    group_id: str,
    group: ScimGroup,
    scim_service: ScimService = Depends(get_scim_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Update Group (Full Replacement)
    RFC 7644 Section 3.5.1
    """
    try:
        if not scim_service.get_group(group_id):
            raise HTTPException(
                status_code=404,
                detail=ScimError(
                    status="404",
                    detail=f"Group {group_id} not found"
                ).model_dump()
            )

        updated_group = scim_service.update_group_members(
            group_id,
            group.members or []
        )
        return updated_group
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/Groups/{group_id}", response_model=ScimGroup)
async def patch_group(
    group_id: str,
    patch_request: ScimPatchRequest,
    scim_service: ScimService = Depends(get_scim_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Patch Group (Partial Update)
    RFC 7644 Section 3.5.2
    Supports adding/removing members
    """
    try:
        patched_group = scim_service.patch_group(
            group_id,
            [op.model_dump() for op in patch_request.Operations]
        )
        if not patched_group:
            raise HTTPException(
                status_code=404,
                detail=ScimError(
                    status="404",
                    detail=f"Group {group_id} not found"
                ).model_dump()
            )
        return patched_group
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

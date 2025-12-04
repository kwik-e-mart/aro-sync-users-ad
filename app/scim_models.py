"""
SCIM 2.0 Models based on RFC 7643 and RFC 7644
https://datatracker.ietf.org/doc/html/rfc7643
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# Common SCIM Meta structure
class ScimMeta(BaseModel):
    resourceType: str
    created: Optional[datetime] = None
    lastModified: Optional[datetime] = None
    location: Optional[str] = None
    version: Optional[str] = None


# SCIM User Email
class ScimEmail(BaseModel):
    value: str
    type: Optional[str] = "work"
    primary: Optional[bool] = True


# SCIM User Name
class ScimName(BaseModel):
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None
    middleName: Optional[str] = None
    honorificPrefix: Optional[str] = None
    honorificSuffix: Optional[str] = None


# SCIM Group Member
class ScimGroupMember(BaseModel):
    value: str  # User ID
    ref: Optional[str] = Field(None, alias="$ref")
    display: Optional[str] = None  # User display name (email)
    type: Optional[str] = "User"


# SCIM User
class ScimUser(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    id: Optional[str] = None
    externalId: Optional[str] = None
    userName: str
    name: Optional[ScimName] = None
    displayName: Optional[str] = None
    emails: Optional[List[ScimEmail]] = None
    active: bool = True
    groups: Optional[List[Dict[str, str]]] = None  # References to groups
    meta: Optional[ScimMeta] = None

    class Config:
        populate_by_name = True


# SCIM Group
class ScimGroup(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    id: Optional[str] = None
    displayName: str
    externalId: Optional[str] = None
    members: Optional[List[ScimGroupMember]] = None
    meta: Optional[ScimMeta] = None

    class Config:
        populate_by_name = True


# SCIM List Response
class ScimListResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    totalResults: int
    startIndex: int = 1
    itemsPerPage: int
    Resources: List[Any]


# SCIM Error Response
class ScimError(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]
    status: str
    scimType: Optional[str] = None
    detail: Optional[str] = None


# SCIM Patch Operation
class ScimPatchOp(BaseModel):
    op: str  # "add", "remove", "replace"
    path: Optional[str] = None
    value: Optional[Any] = None


class ScimPatchRequest(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    Operations: List[ScimPatchOp]


# ServiceProviderConfig
class ScimBulkConfig(BaseModel):
    supported: bool = False
    maxOperations: int = 0
    maxPayloadSize: int = 0


class ScimFilterConfig(BaseModel):
    supported: bool = True
    maxResults: int = 200


class ScimChangePasswordConfig(BaseModel):
    supported: bool = False


class ScimSortConfig(BaseModel):
    supported: bool = False


class ScimEtagConfig(BaseModel):
    supported: bool = False


class ScimAuthenticationScheme(BaseModel):
    type: str
    name: str
    description: str
    specUri: Optional[str] = None
    documentationUri: Optional[str] = None
    primary: bool = True


class ScimPatchConfig(BaseModel):
    supported: bool = True


class ServiceProviderConfig(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"]
    documentationUri: Optional[str] = None
    patch: ScimPatchConfig = ScimPatchConfig()
    bulk: ScimBulkConfig = ScimBulkConfig()
    filter: ScimFilterConfig = ScimFilterConfig()
    changePassword: ScimChangePasswordConfig = ScimChangePasswordConfig()
    sort: ScimSortConfig = ScimSortConfig()
    etag: ScimEtagConfig = ScimEtagConfig()
    authenticationSchemes: List[ScimAuthenticationScheme] = [
        ScimAuthenticationScheme(
            type="oauthbearertoken",
            name="OAuth Bearer Token",
            description="Authentication scheme using the OAuth Bearer Token Standard"
        )
    ]


# Resource Type
class ScimSchemaExtension(BaseModel):
    schema_uri: str = Field(alias="schema")
    required: bool

    class Config:
        populate_by_name = True


class ScimResourceType(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]
    id: str
    name: str
    endpoint: str
    description: str
    schema_uri: str = Field(alias="schema")
    schemaExtensions: Optional[List[ScimSchemaExtension]] = None
    meta: Optional[ScimMeta] = None

    class Config:
        populate_by_name = True


# Schema Definition
class ScimSchemaAttribute(BaseModel):
    name: str
    type: str
    multiValued: bool = False
    description: Optional[str] = None
    required: bool = False
    caseExact: bool = False
    mutability: str = "readWrite"
    returned: str = "default"
    uniqueness: str = "none"
    subAttributes: Optional[List["ScimSchemaAttribute"]] = None


class ScimSchemaDefinition(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    attributes: List[ScimSchemaAttribute]
    meta: Optional[ScimMeta] = None


# Update forward references
ScimSchemaAttribute.model_rebuild()

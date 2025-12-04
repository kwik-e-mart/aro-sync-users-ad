"""
SCIM Service Layer
Bridges SCIM operations with nullplatform sync logic
"""
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from .scim_models import (
    ScimUser, ScimGroup, ScimName, ScimEmail, ScimMeta,
    ScimGroupMember, ScimListResponse, ScimError
)
from .models import User
from .repositories import UserRepository, AuthzRepository
from .config import config


class ScimService:
    def __init__(self, user_repo: UserRepository, authz_repo: AuthzRepository):
        self.user_repo = user_repo
        self.authz_repo = authz_repo
        # Cache for group mappings (grupo -> roles/nrns)
        self._group_mappings: Dict[str, Dict] = {}

    def set_group_mappings(self, mappings: Dict[str, Dict]):
        """
        Set the group mappings from the mapping CSV.
        Format: { "group_name": { "nrn": "...", "roles": ["role1", "role2"] } }
        """
        self._group_mappings = mappings

    def _resolve_nrn(self, nrn: str) -> str:
        """Resolve wildcard NRN to organization NRN"""
        if nrn.strip() == '*':
            return f"organization={config.organization_id}"
        return nrn

    def _parse_name(self, name: Optional[ScimName], email: str) -> Tuple[str, str]:
        """Parse first and last name from SCIM name or email"""
        if name and name.givenName:
            first_name = name.givenName
            last_name = name.familyName or ""
            return first_name, last_name

        # Fall back to email parsing
        if "@" in email:
            local_part = email.split("@")[0]
            if "." in local_part:
                parts = local_part.split(".")
                first_name = parts[0].capitalize()
                last_name = parts[1].capitalize() if len(parts) > 1 else ""
                return first_name, last_name
            return local_part.capitalize(), ""

        return "", ""

    def _internal_user_to_scim(self, user: User, include_groups: bool = True) -> ScimUser:
        """Convert internal User model to SCIM User"""
        # Parse name from username
        first_name, last_name = self._parse_name(None, user.email)
        if " " in user.username:
            parts = user.username.split()
            first_name = parts[0]
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        scim_name = ScimName(
            givenName=first_name,
            familyName=last_name,
            formatted=user.username
        )

        scim_emails = [ScimEmail(value=user.email, type="work", primary=True)]

        groups = []
        if include_groups:
            # Get user grants and map to groups based on group mappings
            try:
                grant_responses = self.authz_repo.client.get_user_grants(int(user.id))
                if grant_responses:
                    for grant_response in grant_responses:
                        for grant in grant_response.grants:
                            # Find matching group(s) for this NRN and role combination
                            for group_name, mapping in self._group_mappings.items():
                                if grant.nrn == mapping.get("nrn") and grant.role.slug in mapping.get("roles", []):
                                    groups.append({
                                        "value": group_name,
                                        "display": group_name,
                                        "$ref": f"/scim/v2/Groups/{group_name}"
                                    })
            except Exception:
                pass  # Groups are optional

        return ScimUser(
            id=user.id,
            userName=user.email,
            name=scim_name,
            displayName=user.username,
            emails=scim_emails,
            active=True,
            groups=groups if groups else None,
            meta=ScimMeta(
                resourceType="User",
                location=f"/scim/v2/Users/{user.id}"
            )
        )

    def _scim_user_to_internal(self, scim_user: ScimUser) -> User:
        """Convert SCIM User to internal User model"""
        email = scim_user.userName
        if scim_user.emails and len(scim_user.emails) > 0:
            email = scim_user.emails[0].value

        username = scim_user.displayName or email.split("@")[0]

        return User(
            id=scim_user.id or "temp",
            username=username,
            email=email,
            roles=[]
        )

    # User Operations
    def get_user(self, user_id: str) -> Optional[ScimUser]:
        """Get a single user by ID"""
        # First, list all users and find by ID
        users = self.user_repo.list_all(status="active")
        for user in users:
            if user.id == user_id:
                return self._internal_user_to_scim(user)
        return None

    def get_user_by_username(self, username: str) -> Optional[ScimUser]:
        """Get a single user by username (email)"""
        user = self.user_repo.get_by_email(username)
        if user:
            return self._internal_user_to_scim(user)
        return None

    def list_users(self, start_index: int = 1, count: int = 100, filter_expr: Optional[str] = None) -> ScimListResponse:
        """List users with pagination and optional filtering"""
        users = self.user_repo.list_all(status="active")

        # Apply filter if provided (basic userName eq filter)
        if filter_expr:
            filtered_users = []
            # Parse simple filter like: userName eq "user@example.com"
            if "userName eq" in filter_expr:
                email = filter_expr.split('"')[1] if '"' in filter_expr else ""
                for user in users:
                    if user.email.lower() == email.lower():
                        filtered_users.append(user)
                users = filtered_users

        # Apply pagination
        start_idx = start_index - 1  # SCIM uses 1-based indexing
        end_idx = start_idx + count
        paginated_users = users[start_idx:end_idx]

        scim_users = [self._internal_user_to_scim(u) for u in paginated_users]

        return ScimListResponse(
            totalResults=len(users),
            startIndex=start_index,
            itemsPerPage=len(scim_users),
            Resources=scim_users
        )

    def create_user(self, scim_user: ScimUser) -> ScimUser:
        """Create a new user"""
        internal_user = self._scim_user_to_internal(scim_user)
        created_user = self.user_repo.create(internal_user)

        # Apply group memberships if provided
        if scim_user.groups:
            for group_ref in scim_user.groups:
                group_name = group_ref.get("value")
                if group_name and group_name in self._group_mappings:
                    mapping = self._group_mappings[group_name]
                    nrns = [n.strip() for n in mapping.get("nrn", "").split(",")]
                    roles = mapping.get("roles", [])

                    for nrn in nrns:
                        resolved_nrn = self._resolve_nrn(nrn)
                        self.authz_repo.update_roles(created_user.id, resolved_nrn, roles)

        return self._internal_user_to_scim(created_user)

    def update_user(self, user_id: str, scim_user: ScimUser) -> Optional[ScimUser]:
        """Update an existing user (PUT - full replacement)"""
        users = self.user_repo.list_all(status="active")
        existing_user = None
        for user in users:
            if user.id == user_id:
                existing_user = user
                break

        if not existing_user:
            return None

        # Update user active status
        if not scim_user.active:
            self.user_repo.delete(user_id)
            return self._internal_user_to_scim(existing_user)

        # Update group memberships
        if scim_user.groups is not None:
            # Clear all existing grants
            grant_responses = self.authz_repo.client.get_user_grants(int(user_id))
            if grant_responses:
                for grant_response in grant_responses:
                    for grant in grant_response.grants:
                        self.authz_repo.client.delete_grant(grant.id)

            # Apply new group memberships
            for group_ref in scim_user.groups:
                group_name = group_ref.get("value")
                if group_name and group_name in self._group_mappings:
                    mapping = self._group_mappings[group_name]
                    nrns = [n.strip() for n in mapping.get("nrn", "").split(",")]
                    roles = mapping.get("roles", [])

                    for nrn in nrns:
                        resolved_nrn = self._resolve_nrn(nrn)
                        self.authz_repo.update_roles(user_id, resolved_nrn, roles)

        return self._internal_user_to_scim(existing_user)

    def patch_user(self, user_id: str, operations: List[Dict]) -> Optional[ScimUser]:
        """Patch an existing user (PATCH - partial update)"""
        users = self.user_repo.list_all(status="active")
        existing_user = None
        for user in users:
            if user.id == user_id:
                existing_user = user
                break

        if not existing_user:
            return None

        # Process SCIM patch operations
        for op in operations:
            op_type = op.get("op", "").lower()
            path = op.get("path", "")
            value = op.get("value")

            if op_type == "replace" and path == "active":
                if not value:
                    self.user_repo.delete(user_id)
                elif value:
                    self.user_repo.reactivate(user_id)

        return self._internal_user_to_scim(existing_user)

    def delete_user(self, user_id: str) -> bool:
        """Delete (deactivate) a user"""
        users = self.user_repo.list_all(status="active")
        user_exists = any(u.id == user_id for u in users)

        if not user_exists:
            return False

        self.user_repo.delete(user_id)
        return True

    # Group Operations
    def get_group(self, group_id: str) -> Optional[ScimGroup]:
        """Get a single group by ID (group_id is the group name)"""
        if group_id not in self._group_mappings:
            return None

        # Get all users in this group
        members = []
        users = self.user_repo.list_all(status="active")
        mapping = self._group_mappings[group_id]
        nrns = [n.strip() for n in mapping.get("nrn", "").split(",")]
        roles = mapping.get("roles", [])

        for user in users:
            try:
                grant_responses = self.authz_repo.client.get_user_grants(int(user.id))
                if grant_responses:
                    for grant_response in grant_responses:
                        for grant in grant_response.grants:
                            for nrn in nrns:
                                resolved_nrn = self._resolve_nrn(nrn)
                                if grant.nrn == resolved_nrn and grant.role.slug in roles:
                                    members.append(ScimGroupMember(
                                        value=user.id,
                                        display=user.email,
                                        ref=f"/scim/v2/Users/{user.id}"
                                    ))
                                    break
            except Exception:
                pass

        return ScimGroup(
            id=group_id,
            displayName=group_id,
            members=members if members else None,
            meta=ScimMeta(
                resourceType="Group",
                location=f"/scim/v2/Groups/{group_id}"
            )
        )

    def list_groups(self, start_index: int = 1, count: int = 100, filter_expr: Optional[str] = None) -> ScimListResponse:
        """List all groups with pagination"""
        group_names = list(self._group_mappings.keys())

        # Apply filter if provided
        if filter_expr and "displayName eq" in filter_expr:
            display_name = filter_expr.split('"')[1] if '"' in filter_expr else ""
            group_names = [g for g in group_names if g == display_name]

        # Apply pagination
        start_idx = start_index - 1
        end_idx = start_idx + count
        paginated_groups = group_names[start_idx:end_idx]

        scim_groups = [self.get_group(g) for g in paginated_groups]

        return ScimListResponse(
            totalResults=len(group_names),
            startIndex=start_index,
            itemsPerPage=len(scim_groups),
            Resources=scim_groups
        )

    def update_group_members(self, group_id: str, members: List[ScimGroupMember]) -> Optional[ScimGroup]:
        """Update group membership (add/remove users from group)"""
        if group_id not in self._group_mappings:
            return None

        mapping = self._group_mappings[group_id]
        nrns = [n.strip() for n in mapping.get("nrn", "").split(",")]
        roles = mapping.get("roles", [])

        # Apply roles to all members
        for member in members:
            user_id = member.value
            for nrn in nrns:
                resolved_nrn = self._resolve_nrn(nrn)
                self.authz_repo.update_roles(user_id, resolved_nrn, roles)

        return self.get_group(group_id)

    def patch_group(self, group_id: str, operations: List[Dict]) -> Optional[ScimGroup]:
        """Patch a group (add/remove members)"""
        if group_id not in self._group_mappings:
            return None

        mapping = self._group_mappings[group_id]
        nrns = [n.strip() for n in mapping.get("nrn", "").split(",")]
        roles = mapping.get("roles", [])

        for op in operations:
            op_type = op.get("op", "").lower()
            path = op.get("path", "")
            value = op.get("value")

            if op_type == "add" and path == "members":
                # Add members to group
                members = value if isinstance(value, list) else [value]
                for member in members:
                    user_id = member.get("value")
                    if user_id:
                        for nrn in nrns:
                            resolved_nrn = self._resolve_nrn(nrn)
                            self.authz_repo.update_roles(user_id, resolved_nrn, roles)

            elif op_type == "remove" and "members" in path:
                # Remove member from group
                # Extract user_id from path like "members[value eq "123"]"
                if "[value eq" in path:
                    user_id = path.split('"')[1] if '"' in path else ""
                    if user_id:
                        for nrn in nrns:
                            resolved_nrn = self._resolve_nrn(nrn)
                            self.authz_repo.update_roles(user_id, resolved_nrn, [])

        return self.get_group(group_id)

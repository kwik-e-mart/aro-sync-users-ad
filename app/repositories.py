from typing import List, Optional
from .models import User
from .client import NullplatformClient


class UserRepository:
    def __init__(self, client: NullplatformClient):
        self.client = client
        self._user_cache: Optional[List[User]] = None
        def _parse_name(self, username: str, email: str) -> tuple[str, str]:
            # Try parsing from username first (e.g., "Carlos Vives", "Carlos Antonio Vives")
            if username and " " in username.strip():
                parts = username.strip().split()
                first_name = parts[0].capitalize()
                last_name = " ".join(parts[1:]).title()
                return first_name, last_name
            
            # Fall back to dot-separated username
            if username and "." in username:
                parts = username.split(".")
                first_name = parts[0].capitalize()
                last_name = parts[1].capitalize() if len(parts) > 1 else ""
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

        return ""

    def list_all(self) -> List[User]:
        nullplatform_users = self.client.list_all_users()

        users = []
        for np_user in nullplatform_users:
            username = np_user.email.split("@")[0]
            user = User(
                id=str(np_user.id),
                username=username,
                email=np_user.email,
                roles=[]
            )
            users.append(user)

        self._user_cache = users
        return users

    def create(self, user: User) -> User:
        first_name, last_name = self._parse_name(user.username, user.email)

        np_user = self.client.create_user(
            email=user.email,
            first_name=first_name,
            last_name=last_name,
        )

        created_user = User(
            id=str(np_user.id),
            username=user.username,
            email=user.email,
            roles=[]
        )

        if self._user_cache is not None:
            self._user_cache.append(created_user)

        return created_user

    def delete(self, user_id: str) -> None:
        self.client.update_user_status(int(user_id), "inactive")

        if self._user_cache is not None:
            self._user_cache = [u for u in self._user_cache if u.id != user_id]

    def get_by_email(self, email: str) -> Optional[User]:
        if self._user_cache is None:
            self.list_all()

        for user in self._user_cache:
            if user.email.lower() == email.lower():
                return user

        return None


class AuthzRepository:
    def __init__(self, client: NullplatformClient):
        self.client = client

    def get_roles(self, user_id: str, nrn: str) -> List[str]:
        grant_responses = self.client.get_user_grants(int(user_id))

        if not grant_responses:
            return []

        roles = []

        for grant_response in grant_responses:
            for grant in grant_response.grants:
                if grant.nrn == nrn:
                    roles.append(grant.role.slug)

        return roles

    def update_roles(self, user_id: str, nrn: str, expected_roles: List[str]) -> None:
        current_grants = self.client.get_user_grants(int(user_id))

        current_role_to_grant_id = {}
        if current_grants:
            for grant_response in current_grants:
                for grant in grant_response.grants:
                    if grant.nrn == nrn:
                        current_role_to_grant_id[grant.role.slug] = grant.id

        current_roles = set(current_role_to_grant_id.keys())
        expected_roles_set = set(expected_roles)

        roles_to_remove = current_roles - expected_roles_set
        roles_to_add = expected_roles_set - current_roles

        for role_slug in roles_to_remove:
            grant_id = current_role_to_grant_id[role_slug]
            try:
                self.client.delete_grant(grant_id)
            except Exception as e:
                print(f"Error deleting grant {grant_id} for role {role_slug}: {e}")

        for role_slug in roles_to_add:
            try:
                self.client.create_grant(int(user_id), role_slug, nrn)
            except Exception as e:
                print(f"Error creating grant for role {role_slug}: {e}")

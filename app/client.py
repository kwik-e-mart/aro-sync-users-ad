import httpx
import time
from typing import Optional, List, Dict, Any
from .config import Config
from .models import TokenResponse, UserListResponse, NullplatformUser, GrantResponse


class NullplatformClient:
    def __init__(self, config: Config):
        self.config = config
        self._token: Optional[str] = None
        self._token_expires_at: Optional[int] = None
        self.http_client = httpx.Client(timeout=30.0)

    def _is_token_expired(self) -> bool:
        if not self._token or not self._token_expires_at:
            return True
        current_time_ms = int(time.time() * 1000)
        return current_time_ms >= self._token_expires_at - 60000

    def get_token(self) -> str:
        if self._is_token_expired():
            response = self.http_client.post(
                f"{self.config.auth_api_url}/token",
                headers={"content-type": "application/json"},
                json={"api_key": self.config.nullplatform_api_key},
            )
            response.raise_for_status()
            token_data = TokenResponse(**response.json())
            self._token = token_data.access_token
            self._token_expires_at = token_data.token_expires_at
        return self._token

    def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        token = self.get_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        response = self.http_client.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def list_users(
        self,
        offset: int = 0,
        limit: int = 100,
        user_type: str = "person",
        status: Optional[str] = None
    ) -> UserListResponse:
        params = {
            "type": user_type,
            "limit": limit,
            "offset": offset,
            "organization_id": self.config.organization_id,
        }
        # Only add status filter if specified (allows fetching all users regardless of status)
        if status:
            params["status"] = status

        response = self._request("GET", f"{self.config.users_api_url}/user/", params=params)
        return UserListResponse(**response.json())

    def list_all_users(self, status: Optional[str] = None) -> List[NullplatformUser]:
        """
        List all users in the organization.

        Args:
            status: Optional status filter ("active", "inactive", or None for all users)
        """
        all_users = []
        offset = 0
        limit = 100

        while True:
            response = self.list_users(offset=offset, limit=limit, status=status)
            all_users.extend(response.results)

            if len(response.results) < limit:
                break

            offset += limit

        return all_users

    def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str
    ) -> NullplatformUser:
        payload = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "organization_id": self.config.organization_id,
        }
        response = self._request(
            "POST",
            f"{self.config.users_api_url}/user/",
            json=payload,
        )
        return NullplatformUser(**response.json())

    def update_user_status(self, user_id: int, status: str) -> None:
        self._request(
            "PATCH",
            f"{self.config.users_api_url}/user/{user_id}",
            json={"status": status},
        )

    def get_user_grants(self, user_id: int) -> List[GrantResponse]:
        params = {
            "user_id": user_id,
            "nrn": f"organization={self.config.organization_id}",
        }
        response = self._request(
            "GET",
            f"{self.config.auth_api_url}/authz/user_role",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [GrantResponse(**item) for item in data]
        return []

    def create_grant(self, user_id: int, role_slug: str, nrn: str) -> Dict[str, Any]:
        payload = {
            "role_slug": role_slug,
            "user_id": user_id,
            "nrn": nrn,
        }
        print(f"Creating grant with payload: {payload} for user_id: {user_id}, role_slug: {role_slug}, nrn: {nrn}")
        response = self._request(
            "POST",
            f"{self.config.auth_api_url}/authz/grants",
            json=payload,
        )
        return response.json()

    def delete_grant(self, grant_id: int) -> None:
        self._request(
            "DELETE",
            f"{self.config.auth_api_url}/authz/grants/{grant_id}",
        )

    def close(self):
        self.http_client.close()

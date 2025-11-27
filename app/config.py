from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    nullplatform_api_key: str
    auth_api_url: str = "https://auth.nullplatform.io"
    users_api_url: str = "https://users.nullplatform.io"

    organization_id: int = 1698562351


config = Config()

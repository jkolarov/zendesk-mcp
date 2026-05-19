from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    zd_subdomain: str
    zd_email: Optional[str] = None
    zd_api_token: Optional[str] = None
    zd_oauth_token: Optional[str] = None
    tools_max_per_page: int = 100
    tools_max_pages: int = 100

    @model_validator(mode="after")
    def validate_auth(self):
        self.auth_method  # fail fast at startup if misconfigured
        return self

    @property
    def zendesk_base_url(self) -> str:
        return f"https://{self.zd_subdomain}.zendesk.com"

    @property
    def auth_method(self) -> str:
        if self.zd_oauth_token:
            return "oauth"
        if self.zd_api_token and self.zd_email:
            return "api_token"
        if self.zd_email and not self.zd_api_token:
            raise ValueError("ZD_API_TOKEN is required when using ZD_EMAIL for API token auth.")
        if self.zd_api_token and not self.zd_email:
            raise ValueError("ZD_EMAIL is required when using ZD_API_TOKEN for API token auth.")
        raise ValueError(
            "Authentication not configured. Provide either ZD_OAUTH_TOKEN, "
            "or both ZD_EMAIL and ZD_API_TOKEN."
        )


settings = Settings()

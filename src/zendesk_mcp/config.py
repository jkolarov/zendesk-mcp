from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    zd_subdomain: str
    zd_email: Optional[str] = None
    zd_api_token: Optional[str] = None
    # Static OAuth access token (expires up to 30 days; lower priority than client credentials)
    zd_oauth_token: Optional[str] = None
    # OAuth Client Credentials — permanent credentials, token minted at startup
    zd_oauth_client_id: Optional[str] = None
    zd_oauth_client_secret: Optional[str] = None
    zd_oauth_scope: str = "read write"
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
        # Priority 1: Static OAuth access token (pre-generated; overrides everything else
        # so that an explicitly-provided token is never silently ignored)
        if self.zd_oauth_token:
            return "oauth_static"
        # Priority 2: OAuth Client Credentials (permanent credentials, no expiry)
        if self.zd_oauth_client_id or self.zd_oauth_client_secret:
            if not self.zd_oauth_client_id:
                raise ValueError(
                    "ZD_OAUTH_CLIENT_SECRET is set but ZD_OAUTH_CLIENT_ID is missing."
                )
            if not self.zd_oauth_client_secret:
                raise ValueError(
                    "ZD_OAUTH_CLIENT_ID is set but ZD_OAUTH_CLIENT_SECRET is missing."
                )
            return "oauth_client_credentials"
        # Priority 3: API token (email + token pair)
        if self.zd_api_token and self.zd_email:
            return "api_token"
        if self.zd_email and not self.zd_api_token:
            raise ValueError("ZD_API_TOKEN is required when using ZD_EMAIL for API token auth.")
        if self.zd_api_token and not self.zd_email:
            raise ValueError("ZD_EMAIL is required when using ZD_API_TOKEN for API token auth.")
        raise ValueError(
            "Authentication not configured. Provide one of:\n"
            "  • ZD_OAUTH_CLIENT_ID + ZD_OAUTH_CLIENT_SECRET (recommended)\n"
            "  • ZD_OAUTH_TOKEN (static access token)\n"
            "  • ZD_EMAIL + ZD_API_TOKEN"
        )


settings = Settings()

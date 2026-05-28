from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    zd_subdomain: str
    zd_email: Optional[str] = None
    zd_api_token: Optional[str] = None
    # OAuth — static pre-generated access token
    zd_oauth_token: Optional[str] = None
    # OAuth — refresh token flow (recommended): admin generates a refresh token once,
    # the server mints short-lived access tokens from it automatically
    zd_oauth_client_id: Optional[str] = None
    zd_oauth_client_secret: Optional[str] = None
    zd_oauth_refresh_token: Optional[str] = None
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
        # Priority 1: Static OAuth access token (pre-generated; overrides everything else)
        if self.zd_oauth_token:
            return "oauth_static"
        # Priority 2: OAuth Refresh Token flow — admin generates a refresh token once,
        # server mints short-lived access tokens automatically
        if self.zd_oauth_client_id or self.zd_oauth_client_secret or self.zd_oauth_refresh_token:
            missing = [
                name for name, val in [
                    ("ZD_OAUTH_CLIENT_ID", self.zd_oauth_client_id),
                    ("ZD_OAUTH_CLIENT_SECRET", self.zd_oauth_client_secret),
                    ("ZD_OAUTH_REFRESH_TOKEN", self.zd_oauth_refresh_token),
                ] if not val
            ]
            if missing:
                raise ValueError(
                    f"OAuth refresh token auth is incomplete. Missing: {', '.join(missing)}.\n"
                    "All three are required: ZD_OAUTH_CLIENT_ID, ZD_OAUTH_CLIENT_SECRET, ZD_OAUTH_REFRESH_TOKEN."
                )
            return "oauth_refresh_token"
        # Priority 3: API token (email + token pair)
        if self.zd_api_token and self.zd_email:
            return "api_token"
        if self.zd_email and not self.zd_api_token:
            raise ValueError("ZD_API_TOKEN is required when using ZD_EMAIL for API token auth.")
        if self.zd_api_token and not self.zd_email:
            raise ValueError("ZD_EMAIL is required when using ZD_API_TOKEN for API token auth.")
        raise ValueError(
            "Authentication not configured. Provide one of:\n"
            "  • ZD_OAUTH_CLIENT_ID + ZD_OAUTH_CLIENT_SECRET + ZD_OAUTH_REFRESH_TOKEN (recommended)\n"
            "  • ZD_OAUTH_TOKEN (static access token)\n"
            "  • ZD_EMAIL + ZD_API_TOKEN"
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

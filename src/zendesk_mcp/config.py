from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    zd_subdomain: str
    zd_email: Optional[str] = None
    zd_api_token: Optional[str] = None
    zd_oauth_token: Optional[str] = None
    tools_max_per_page: int = 100
    tools_max_pages: int = 100

    @property
    def zendesk_base_url(self) -> str:
        return f"https://{self.zd_subdomain}.zendesk.com"

    @property
    def auth_method(self) -> str:
        if self.zd_oauth_token:
            return "oauth"
        if self.zd_api_token and self.zd_email:
            return "api_token"
        raise ValueError(
            "Authentication not configured. Provide either ZD_OAUTH_TOKEN, "
            "or both ZD_EMAIL and ZD_API_TOKEN."
        )


settings = Settings()

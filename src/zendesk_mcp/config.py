from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    zd_subdomain: str
    zd_email: str
    zd_api_token: str
    tools_max_per_page: int = 100
    tools_max_pages: int = 100

    @property
    def zendesk_base_url(self) -> str:
        return f"https://{self.zd_subdomain}.zendesk.com"

    @property
    def zendesk_auth(self) -> str:
        return f"{self.zd_email}/token:{self.zd_api_token}"


settings = Settings()

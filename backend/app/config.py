from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str

    # Microsoft Graph (reads GRAPH_* env vars)
    graph_client_id: str = ""
    graph_client_secret: str = ""
    graph_tenant_id: str = ""
    graph_mailbox: str = "sathishkumar@jmangroup.com"

    # Webhook base URL — must be public HTTPS in production; use ngrok locally
    webhook_base_url: str = "http://localhost:8000"

    nextauth_secret: str = ""
    nextauth_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

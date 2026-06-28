from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = ""
    openai_api_key: str

    # Azure PostgreSQL (AAD token auth)
    azure_pg_host: str = ""
    azure_pg_user: str = ""
    azure_pg_port: int = 5432
    azure_pg_database: str = "postgres"

    # Microsoft Graph (reads GRAPH_* env vars)
    graph_client_id: str = ""
    graph_client_secret: str = ""
    graph_tenant_id: str = ""
    graph_mailbox: str = "sathishkumar@jmangroup.com"

    # Webhook base URL — must be public HTTPS in production; use ngrok locally
    webhook_base_url: str = "http://localhost:8000"

    # Azure Communication Services Email
    acs_connection_string: str = ""
    acs_sender_email: str = "DoNotReply@e3445e90-bf10-44d1-8ea3-32eb935710d6.azurecomm.net"

    nextauth_secret: str = ""
    nextauth_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

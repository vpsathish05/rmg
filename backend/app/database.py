import subprocess
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _get_azure_token() -> str:
    """Fetch a fresh AAD access token for Azure PostgreSQL."""
    result = subprocess.run(
        ["az", "account", "get-access-token",
         "--resource", "https://ossrdbms-aad.database.windows.net",
         "--query", "accessToken", "--output", "tsv"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _build_engine():
    if settings.database_url:
        # Static connection string
        return create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    elif settings.azure_pg_host:
        # Azure AD token auth
        url = (
            f"postgresql://{settings.azure_pg_user}:"
            f"{{token}}@{settings.azure_pg_host}:{settings.azure_pg_port}"
            f"/{settings.azure_pg_database}?sslmode=require"
        )
        token = _get_azure_token()
        actual_url = url.replace("{token}", token)
        eng = create_engine(
            actual_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )

        @event.listens_for(eng, "do_connect")
        def provide_token(dialect, conn_rec, cargs, cparams):
            cparams["password"] = _get_azure_token()

        return eng
    else:
        raise RuntimeError("No database configuration found. Set DATABASE_URL or AZURE_PG_HOST.")


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

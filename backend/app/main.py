import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.routers import employees, projects, allocations, recommend, forecast, health, dashboard
from app.routers import webhooks, rmg_engine

log = logging.getLogger(__name__)


async def _register_graph_webhook(app: FastAPI) -> None:
    """Register Microsoft Graph subscription on startup (if configured)."""
    from app.config import settings
    from app.services.graph import create_subscription

    if not settings.graph_client_id:
        log.info("Graph credentials not set — email webhook disabled.")
        return

    if not settings.webhook_base_url.startswith("https://"):
        log.warning(
            "WEBHOOK_BASE_URL is not HTTPS (%s). "
            "Microsoft Graph requires a public HTTPS endpoint. "
            "Use ngrok for local dev: ngrok http 8000",
            settings.webhook_base_url,
        )
        return

    notification_url = f"{settings.webhook_base_url.rstrip('/')}/api/webhooks/email"
    try:
        sub = await create_subscription(
            tenant=settings.graph_tenant_id,
            client_id=settings.graph_client_id,
            client_secret=settings.graph_client_secret,
            mailbox=settings.graph_mailbox,
            notification_url=notification_url,
        )
        app.state.graph_subscription_id = sub["id"]
        log.info("Graph subscription registered: %s → %s", sub["id"], notification_url)

        # Schedule renewal every 47 hours (subscriptions expire after 3 days)
        asyncio.create_task(_renew_loop(app))
    except Exception as e:
        log.error("Failed to register Graph subscription: %s", e)


async def _renew_loop(app: FastAPI) -> None:
    from app.config import settings
    from app.services.graph import renew_subscription
    while True:
        await asyncio.sleep(47 * 3600)
        sub_id = getattr(app.state, "graph_subscription_id", None)
        if sub_id:
            try:
                await renew_subscription(
                    settings.graph_tenant_id,
                    settings.graph_client_id,
                    settings.graph_client_secret,
                    sub_id,
                )
                log.info("Graph subscription renewed: %s", sub_id)
            except Exception as e:
                log.error("Renewal failed: %s", e)


async def _daily_recommend_job():
    """Nightly 2am IST: pre-compute all Not Resourced role recommendations."""
    from app.database import SessionLocal
    from app.services import rec_cache
    log.info("Nightly recommendation job starting…")
    db = SessionLocal()
    try:
        result = await rec_cache.compute_all(db)
        log.info("Nightly recommendation job done: %s", result)
    except Exception as exc:
        log.error("Nightly recommendation job failed: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _register_graph_webhook(app)

    # Daily 2am IST recommendation pre-compute
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(_daily_recommend_job, "cron", hour=2, minute=0)
    scheduler.start()
    log.info("Scheduler started — daily recommendation compute at 02:00 IST")

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(title="RMG API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(dashboard.router,    prefix="/api/dashboard",  tags=["dashboard"])
app.include_router(employees.router,    prefix="/api/employees",  tags=["employees"])
app.include_router(projects.router,     prefix="/api/projects",   tags=["projects"])
app.include_router(allocations.router,  prefix="/api/allocations", tags=["allocations"])
app.include_router(recommend.router,    prefix="/api/recommend",  tags=["recommend"])
app.include_router(forecast.router,     prefix="/api/forecast",   tags=["forecast"])
app.include_router(rmg_engine.router,   prefix="/api/rmg",        tags=["rmg-engine"])
app.include_router(webhooks.router,     prefix="/api/webhooks/email", tags=["webhooks"])

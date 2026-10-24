import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings, get_detected_os
from .api import router
from .executor.browser import browser_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("agentos.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os_info = get_detected_os()
    logger.info("=" * 60)
    logger.info("🚀 AgentOS Desktop Agent Service Starting")
    logger.info(f"   Platform: {os_info['platform_string']}")
    logger.info(f"   Host: {settings.desktop_host}:{settings.desktop_port}")
    logger.info(f"   Workspace: {settings.allowed_workspace}")
    logger.info(f"   ASI1 Configured: {bool(settings.asi1_api_key)} (Model: {settings.asi1_model})")
    if not settings.asi1_api_key:
        logger.info("   Mode: Local Deterministic Demo Mode (Configure ASI1_API_KEY for live LLM)")
    else:
        logger.info("   Mode: Live Fetch.ai ASI:One Active")
    logger.info("=" * 60)
    yield
    logger.info("Shutting down AgentOS Desktop Service...")
    await browser_manager.close()
    logger.info("Clean shutdown complete.")


app = FastAPI(
    title="AgentOS Desktop Service",
    description="Cross-platform AI desktop operator backend with Fetch.ai ASI:One integration",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local React / Tauri dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Loopback desktop dashboard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.desktop_host,
        port=settings.desktop_port,
        reload=False
    )

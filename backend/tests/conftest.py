import socket
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.session import engine
from app.main import app


def _check_db_connectivity() -> bool:
    try:
        host = settings.POSTGRES_HOST or "localhost"
        port = int(settings.POSTGRES_PORT or 5432)
        s = socket.create_connection((host, port), timeout=0.4)
        s.close()
        return True
    except Exception:
        return False


DB_AVAILABLE = _check_db_connectivity()


def pytest_collection_modifyitems(config, items):
    if not DB_AVAILABLE:
        skip_db = pytest.mark.skip(
            reason="PostgreSQL database container offline - skipping integration tests requiring live DB connection"
        )
        for item in items:
            if "integration" in str(item.fspath):
                # Standalone integration tests that do not query live DB
                if item.name not in (
                    "test_health_liveness",
                    "test_health_live_probe",
                    "test_api_v1_info",
                    "test_request_id_generated_automatically",
                    "test_custom_request_id_propagated",
                    "test_01_yolo_object_detection",
                    "test_02_anpr_plate_localization_and_ocr",
                    "test_03_yolo_anpr_combined_video_processing",
                ):
                    item.add_marker(skip_db)



@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client fixture connected directly to the FastAPI ASGI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
    await engine.dispose()

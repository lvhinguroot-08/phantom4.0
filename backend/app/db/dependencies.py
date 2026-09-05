from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.core.logging import logger


async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    FastAPI dependency yielding an async database session per request.
    Handles commit, rollback, and cleanup cleanly across exception propagation.
    """
    session = None
    try:
        session = AsyncSessionLocal()
        yield session
        if session:
            try:
                await session.commit()
            except Exception:
                pass
    except Exception:
        if session:
            try:
                await session.rollback()
            except Exception:
                pass
        raise
    finally:
        if session:
            try:
                await session.close()
            except Exception:
                pass


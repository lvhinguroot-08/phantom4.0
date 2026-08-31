from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.core.logging import logger


async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    FastAPI dependency yielding an async database session per request.
    Gracefully yields None if database is unreachable or disconnected.
    """
    session = None
    try:
        session = AsyncSessionLocal()
        yield session
        try:
            await session.commit()
        except Exception:
            pass
    except Exception as e:
        if session:
            try:
                await session.rollback()
            except Exception:
                pass
        logger.debug(f"Database session error in get_db: {e}")
        yield None
    finally:
        if session:
            try:
                await session.close()
            except Exception:
                pass

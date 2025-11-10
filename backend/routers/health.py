# Health router
from fastapi import APIRouter

from utils import logger

router = APIRouter()


@router.get("/health")
def health():
    logger.debug("🏥 Health check requested")
    return {"status": "ok"}

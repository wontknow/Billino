# Health router
from fastapi import APIRouter

from utils import logger

router = APIRouter()


@router.get("/health", tags=["health"])
def health():
    """
    Health check endpoint.
    
    Returns the current status of the API.
    
    **Returns:**
    - `status` (string): API status ("ok" if healthy)
    
    **Example Response:**
    ```json
    {
        "status": "ok"
    }
    ```
    """
    logger.debug("🏥 Health check requested")
    return {"status": "ok"}

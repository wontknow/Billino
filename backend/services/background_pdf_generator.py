"""
Helper class for background PDF generation using daemon threads.
Centralizes the threading logic for async PDF generation after invoice creation.
"""

import threading
from typing import Callable

from sqlmodel import Session

from database import get_engine
from utils import logger


class BackgroundPDFGenerator:
    """
    Helper class to manage background PDF generation in daemon threads.

    This class encapsulates the pattern of:
    1. Creating a new database session in a background thread
    2. Executing PDF generation function with proper error handling
    3. Ensuring session cleanup in all cases
    """

    @staticmethod
    def generate_in_background(
        pdf_generation_func: Callable[..., bool],
        entity_id: int,
        entity_type: str,
        thread_name_prefix: str = "PDF",
        **kwargs,
    ) -> threading.Thread:
        """
        Execute a PDF generation function in a background daemon thread.

        Args:
            pdf_generation_func: Function that takes (session, entity_id, **kwargs) and returns bool.
            entity_id: ID of the invoice/summary invoice to generate a PDF for.
            entity_type: Type of entity (e.g., "invoice", "summary invoice") for logging.
            thread_name_prefix: Prefix for the thread name (default: "PDF").
            **kwargs: Additional keyword arguments to pass to pdf_generation_func.

        Returns:
            threading.Thread: The started daemon thread (for testing purposes).

        Example:
            BackgroundPDFGenerator.generate_in_background(
                pdf_generation_func=generate_pdf_for_invoice,
                entity_id=invoice.id,
                entity_type="invoice",
            )
        """
        def generate_pdf_background():
            """Nested function that runs in the background thread"""
            engine = get_engine()
            bg_session = Session(engine)
            try:
                logger.debug(
                    f"🖨️ [THREAD] Generating PDF for {entity_type} {entity_id} in background..."
                )
                result = pdf_generation_func(bg_session, entity_id, **kwargs)
                logger.info(f"✅ [THREAD] PDF generation result: {result}")
            except Exception as e:
                logger.error(
                    f"❌ [THREAD] Background PDF generation failed for {entity_type} {entity_id}: {str(e)}",
                    exc_info=True,
                )
            finally:
                bg_session.close()

        # Create and start the daemon thread
        pdf_thread = threading.Thread(
            target=generate_pdf_background,
            daemon=True,
            name=f"{thread_name_prefix}-{entity_id}",
        )
        logger.debug(f"🖨️ Thread created: {pdf_thread.name}")
        pdf_thread.start()
        logger.debug(f"🖨️ Thread started")

        return pdf_thread

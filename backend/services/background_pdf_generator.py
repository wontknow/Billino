"""
Helper class for background PDF generation using daemon threads.
Centralizes the threading logic for async PDF generation after invoice creation.

Note on daemon threads:
- Daemon threads are terminated immediately when the main process exits
- This means PDFs may not complete during server shutdown/restart
- PDFs can be regenerated on-demand via the lazy-load fallback mechanism
- For production deployments, consider using a proper task queue (Celery, RQ, etc.)
"""

import atexit
import threading
from typing import Callable, Set

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
    4. Tracking active threads for graceful shutdown

    Graceful shutdown behavior:
    - Tracks all active PDF generation threads
    - Provides a method to wait for in-flight generations during shutdown
    - Automatically registered with atexit for process termination
    """

    _active_threads: Set[threading.Thread] = set()
    _lock = threading.Lock()
    _shutdown_timeout = 5.0  # Maximum seconds to wait for threads during shutdown

    @classmethod
    def generate_in_background(
        cls,
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
                # Remove thread from active set when complete
                with cls._lock:
                    cls._active_threads.discard(pdf_thread)

        # Create and start the daemon thread
        pdf_thread = threading.Thread(
            target=generate_pdf_background,
            daemon=True,
            name=f"{thread_name_prefix}-{entity_id}",
        )
        logger.debug(f"🖨️ Thread created: {pdf_thread.name}")

        # Track thread in active set
        with cls._lock:
            cls._active_threads.add(pdf_thread)

        pdf_thread.start()
        logger.debug(f"🖨️ Thread started")

        return pdf_thread

    @classmethod
    def wait_for_active_threads(cls, timeout: float = None) -> bool:
        """
        Wait for all active PDF generation threads to complete.

        This method should be called during graceful shutdown to ensure
        in-flight PDF generations have a chance to complete before the
        process terminates.

        Args:
            timeout: Maximum time to wait in seconds. Uses class default if None.

        Returns:
            bool: True if all threads completed within timeout, False otherwise.
        """
        if timeout is None:
            timeout = cls._shutdown_timeout

        logger.info(f"⏳ Waiting for {len(cls._active_threads)} PDF generation threads...")

        # Get a snapshot of active threads
        with cls._lock:
            threads = list(cls._active_threads)

        # Wait for each thread with proportional timeout
        thread_timeout = timeout / len(threads) if threads else 0
        for thread in threads:
            thread.join(timeout=thread_timeout)
            if thread.is_alive():
                logger.warning(
                    f"⚠️ Thread {thread.name} did not complete within timeout"
                )

        # Check if any threads are still alive
        remaining = sum(1 for t in threads if t.is_alive())
        if remaining > 0:
            logger.warning(
                f"⚠️ {remaining} PDF generation thread(s) incomplete after {timeout}s timeout"
            )
            return False

        logger.info("✅ All PDF generation threads completed")
        return True

    @classmethod
    def _shutdown_handler(cls):
        """Handler called on process exit to wait for active threads."""
        if cls._active_threads:
            logger.info("🛑 Shutdown detected - waiting for PDF generation threads...")
            cls.wait_for_active_threads()


# Register shutdown handler to wait for threads on process exit
atexit.register(BackgroundPDFGenerator._shutdown_handler)

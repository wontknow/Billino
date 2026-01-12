"""
Structured error handling for Billino backend.

Provides:
- Custom exception types for different error scenarios
- Structured error responses for API endpoints
- Error context information for debugging
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ErrorCategory(str, Enum):
    """Error categories for structured error handling."""

    STARTUP = "startup_error"
    DATABASE = "database_error"
    VALIDATION = "validation_error"
    BUSINESS_LOGIC = "business_logic_error"
    EXTERNAL_SERVICE = "external_service_error"
    INTERNAL = "internal_error"


class ErrorResponse(BaseModel):
    """
    Structured error response for API endpoints.

    Used for all API errors to provide consistent error information
    to frontend and diagnostic tools.
    """

    category: ErrorCategory
    message: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class BillinoError(Exception):
    """Base exception for all Billino errors."""

    def __init__(
        self,
        category: ErrorCategory,
        message: str,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.category = category
        self.message = message
        self.detail = detail or ""
        self.context = context or {}
        super().__init__(self.message)

    def to_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert exception to ErrorResponse for API."""
        return ErrorResponse(
            category=self.category,
            message=self.message,
            detail=self.detail,
            request_id=request_id,
            context=self.context,
        )

    def __str__(self) -> str:
        """String representation for logging."""
        parts = [f"[{self.category}] {self.message}"]
        if self.detail:
            parts.append(f"Detail: {self.detail}")
        if self.context:
            parts.append(f"Context: {self.context}")
        return " | ".join(parts)


class StartupError(BillinoError):
    """Raised when backend startup fails."""

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(ErrorCategory.STARTUP, message, detail, context)


class DatabaseError(BillinoError):
    """Raised when database operation fails."""

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(ErrorCategory.DATABASE, message, detail, context)


class ValidationError(BillinoError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(ErrorCategory.VALIDATION, message, detail, context)


class BusinessLogicError(BillinoError):
    """Raised when business logic constraint is violated."""

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(ErrorCategory.BUSINESS_LOGIC, message, detail, context)


class ExternalServiceError(BillinoError):
    """Raised when external service call fails."""

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(ErrorCategory.EXTERNAL_SERVICE, message, detail, context)


class InternalError(BillinoError):
    """Raised for unexpected internal errors."""

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(ErrorCategory.INTERNAL, message, detail, context)


# Common error messages
class ErrorMessages:
    """Standard error messages for consistency."""

    PORT_ALREADY_BOUND = (
        "Backend port is already in use. "
        "Check for running instances or change BACKEND_PORT."
    )
    DATABASE_INITIALIZATION_FAILED = (
        "Failed to initialize database. Check database path and permissions."
    )
    DATABASE_CONNECTION_FAILED = (
        "Failed to connect to database. Database may be locked or corrupted."
    )
    INVALID_CONFIGURATION = "Backend configuration is invalid."
    GRACEFUL_SHUTDOWN_TIMEOUT = "Graceful shutdown timeout exceeded."
    MISSING_REQUIRED_CONFIG = "Missing required configuration variable: {var}"


def format_error_message(template: str, **kwargs) -> str:
    """Format error message with context."""
    return template.format(**kwargs) if kwargs else template

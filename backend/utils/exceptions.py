"""
Accura – Custom Exception Classes
"""

from sanic.exceptions import SanicException


class AccuraException(SanicException):
    """Base exception for all Accura errors."""

    status_code = 500
    message = "Internal server error"


class AuthenticationError(AccuraException):
    status_code = 401
    message = "Authentication failed"


class AuthorizationError(AccuraException):
    status_code = 403
    message = "Insufficient permissions"


class NotFoundError(AccuraException):
    status_code = 404
    message = "Resource not found"


class ValidationError(AccuraException):
    status_code = 422
    message = "Validation error"


class RateLimitError(AccuraException):
    status_code = 429
    message = "Rate limit exceeded"


class QuotaExceededError(AccuraException):
    status_code = 429
    message = "Usage quota exceeded for your subscription tier"


class AIProviderError(AccuraException):
    status_code = 502
    message = "AI provider returned an error"


class TimeoutError(AccuraException):
    status_code = 504
    message = "Agent response timed out"


class MCPServerError(AccuraException):
    status_code = 502
    message = "MCP server communication failed"


class BillingError(AccuraException):
    status_code = 402
    message = "Billing error"

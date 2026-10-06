"""Exceptions for the Skylight API client library."""

from typing import Any


class SkylightError(Exception):
    """Base exception for all Skylight client errors."""

    def __init__(self, message: str = "", *args: Any) -> None:
        self.message = message
        super().__init__(message, *args)


class SkylightAuthError(SkylightError):
    """Raised when authentication fails and cannot be recovered.

    Callers should treat this as "re-authentication required" (in Home
    Assistant terms: raise ConfigEntryAuthFailed).
    """


class SkylightAPIError(SkylightError):
    """Raised on non-401 HTTP failures and transport-level problems."""

    def __init__(
        self,
        message: str = "",
        status_code: int | None = None,
        response_body: str | None = None,
        *args: Any,
    ) -> None:
        super().__init__(message, *args)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        if self.status_code:
            return f"{self.message} (HTTP {self.status_code})"
        return self.message

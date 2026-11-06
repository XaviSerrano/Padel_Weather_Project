class ConfigurationError(Exception):
    """Raised when a required application setting is missing or invalid."""


class ExternalServiceError(Exception):
    """Raised when an external data provider cannot return usable data."""

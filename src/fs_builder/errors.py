"""Project-level exceptions."""


class FSBuilderError(Exception):
    """Base error for user-facing command failures."""


class ConfigError(FSBuilderError):
    """Raised when configuration is missing or invalid."""


class CLIError(FSBuilderError):
    """Raised for invalid CLI usage that passes argparse parsing."""


class PlanValidationError(FSBuilderError):
    """Raised when a plan cannot be parsed or validated."""

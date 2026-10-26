"""canopus-humanizer REST API subpackage."""

from canopus_humanizer.api.errors import register_exception_handlers
from canopus_humanizer.api.schemas import ErrorResponse

__all__ = ["register_exception_handlers", "ErrorResponse"]

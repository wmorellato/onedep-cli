class OneDepManagerError(Exception):
    """Base class for all onedep_manager domain errors."""


class ServiceNotFoundError(OneDepManagerError):
    """A requested service is not present in the configuration."""


class HandlerLoadError(OneDepManagerError):
    """A service handler class could not be loaded."""

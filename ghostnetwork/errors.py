"""GhostNetwork domain exceptions."""


class GhostNetworkError(Exception):
    """Base class for GhostNetwork domain failures."""


class CycleNotFound(GhostNetworkError):
    pass


class CycleAlreadyActive(GhostNetworkError):
    pass


class CycleLocked(GhostNetworkError):
    pass


class PartNotFound(GhostNetworkError):
    pass


class ReservationConflict(GhostNetworkError):
    pass


class ReservationExpired(GhostNetworkError):
    pass


class InvalidStateTransition(GhostNetworkError):
    pass


class InvalidPartStateTransition(InvalidStateTransition):
    pass


class RepositoryIntegrityError(GhostNetworkError):
    pass


class TopologyGenerationError(RepositoryIntegrityError):
    pass

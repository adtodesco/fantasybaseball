class FantasyBaseballError(ValueError):
    """Base fantasy baseball error class"""
    pass


class InvalidRequest(FantasyBaseballError):
    """The provided parameters create and invalid request."""
    pass


class FileDoesNotExist(FantasyBaseballError):
    """The file does not exist"""
    pass

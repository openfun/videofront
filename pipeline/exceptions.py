class LockUnavailable(Exception):
    """
    Raised whenever we try to acquire a lock that was already acquired.
    """
    pass


class TranscodingFailed(Exception):
    """
    Raised whenever a transcoding task failed.
    """
    pass


class SubtitleInvalid(Exception):
    """
    Raised whenever subtitle cannot be converted to utf8 or to VTT format.
    """
    pass

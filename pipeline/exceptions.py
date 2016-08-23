class VideoNotUploaded(Exception):
    """
    Raised whenever a video was not uploaded. Note that this may cover upload
    errors, but also cases when an upload url was not used.
    """
    pass


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

class SubtitlesInvalid(Exception):
    """
    Raised whenever subtitles cannot be converted to utf8 or to VTT format.
    """
    pass

import importlib
from django.conf import settings


class BaseBackend(object):

    # Default suffix (and implied format ) for converted thumbnails. Change
    # this value if you intend to serve thumbnails with a different format.
    THUMBNAILS_SUFFIX = '.jpg'

    def upload_video(self, video_id, file_object):
        """
        Store a video file for transcoding.

        Args:
            video_id (str)
            file_object (str)
        """
        raise NotImplementedError

    def start_transcoding(self, video_id):
        """
        Create and start transcoding jobs.

        Returns:
            jobs: iterable of arbitrary job objects. Each of these job objects
            will be passed as argument to the `check_progress` method
        """
        raise NotImplementedError

    def check_progress(self, job):
        """
        Monitor the progress of a transcoding job. This method will be called
        periodically by the transcoding task.

        Args:
            job: arbitrary object that was returned by the `start_transcoding` method

        Returns:
            progress (float): progress percentage with a value between 0 and 100
            finished (bool): True if the job is finished

        Raises:
            TranscodingError in case of transcoding error. The exception
            message will be logged in the transcoding job.
        """
        raise NotImplementedError

    def delete_video(self, video_id):
        """
        Delete all resources associated to a video. E.g: in case of transcoding
        error, but also whenever a video is deleted by its owner.
        """
        raise NotImplementedError

    def delete_subtitle(self, video_id, subtitle_id):
        """
        Delete subtitle from a video.
        """
        raise NotImplementedError

    def video_url(self, video_id, format_name):
        """
        Return the url from which the video can be streamed or downloaded, with
        the given format. This is the url that will be passed to the html5
        video player.

        Note that there will be one call to this method for every format and
        for every video object, at every call to the videos API. So the result
        of this method should either be fast, or cached.
        """
        raise NotImplementedError

    def iter_formats(self, video_id):
        """
        Iterator on the available formats for that video. This method will be
        called after transcoding has finished.

        Yields:
            format_name (str)
            bitrate (float)
        """
        raise NotImplementedError

    def upload_subtitle(self, video_id, subtitle_id, language_code, content):
        """
        Upload a video subtitle file. Raise a SubtitleInvalid in case the
        subtitle is in an invalid format.

        Args:
            video_id (str)
            subtitle_id (str)
            language_code (str)
            content (bytes)
        """
        raise NotImplementedError

    def upload_thumbnail(self, video_id, file_object):
        """
        Upload a video thumbnail file.

        Args:
            video_id (str)
            file_object (file)
        """
        raise NotImplementedError

    def subtitle_url(self, video_id, subtitle_id, language_code):
        """
        Returns the url at which the subtitle file can be downloaded. Note
        that this method once for every subtitle object for every API videos
        API call. So the result of this result should either be fast or cached.
        """
        raise NotImplementedError

    def thumbnail_url(self, video_id):
        """
        Returns the url at which the video thumbnail can be downloaded. This
        should be a fast method.

        This feature is optional. If undefined, the thumbnail url will be an
        empty string.
        """
        return ''


class UndefinedPluginBackend(Exception):
    pass


class MissingPluginBackend(Exception):
    pass


def get():
    """
    Get the plugin backend based on the PLUGIN_BACKEND setting.

    Raises:
        UndefinedPluginBackend in case of undefined setting
        ImportError in case of missing module
        MissingPluginBackend in case of a missing plugin class definition

    """
    setting = getattr(settings, 'PLUGIN_BACKEND')
    if setting is None:
        raise UndefinedPluginBackend()

    if hasattr(setting, '__call__'):
        backend_object = setting()
    else:
        module_name, object_name = setting.rsplit(".", 1)
        backend_module = importlib.import_module(module_name)
        backend_class = getattr(backend_module, object_name, None)
        if backend_class is None:
            raise MissingPluginBackend(setting)
        # Note that we could cache the plugin backend across calls; we don't do
        # it for now, because it's not really useful.
        backend_object = backend_class()

    return backend_object

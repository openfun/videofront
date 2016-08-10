import importlib
from django.conf import settings


class BaseBackend(object):

    def create_upload_url(self, filename):
        """
        Return an upload url for uploading video files.

        Args:
            filename (str): name of the file that will be uploaded

        Returns:
            {
                'url' (str): url on which the video file can be sent
                'method': 'GET', 'POST' or 'PUT'
                'expires_at': timestamp at which the url will expire
                'id': public video id
            }
        """
        raise NotImplementedError

    def get_uploaded_video(self, video_id):
        """
        Get the video file for which an upload url was generated.

        This function is only used to check whether an upload url has been used or not.

        If the upload url has not been used yet, this function should raise a
        VideoNotUploaded exception.

        The return value is not used.
        """
        raise NotImplementedError

    def create_transcoding_jobs(self, video_id):
        """
        Create and start transcoding jobs.

        Returns:
            jobs: iterable of arbitrary job objects. Each of these job objects
            will be passed as argument to the `get_transcoding_job_progress`
            method
        """
        raise NotImplementedError

    def get_transcoding_job_progress(self, job):
        """
        Monitor the progress of a transcoding job. This method will be called
        periodically by the transcoding task.

        Args:
            job: arbitrary object that was returned by the `create_transcoding_job` method

        Returns:
            progress (float): progress percentage with a value between 0 and 100
            finished (bool): True if the job is finished

        Raises:
            TranscodingError in case of transcoding error. The exception
            message will be logged in the transcoding job.
        """
        raise NotImplementedError

    def delete_resources(self, video_id):
        """
        Delete all resources associated to a video. E.g: in case of transcoding error.
        """
        raise NotImplementedError

    def get_video_streaming_url(self, video_id, format_name):
        """
        Return the url from which the video can be streamed, with the given
        format. This is the url that will be passed to the html5 video player.

        Note that there will be one call to this method for every format and
        for every video object, at every call to the videos API. So the result
        of this method should either be fast, or cached.
        """
        raise NotImplementedError

    def iter_available_formats(self, video_id):
        """
        Iterator on the available formats for that video. This method will be
        called after transcoding has finished.

        Yields:
            format_name (str)
            bitrate (float)
        """
        raise NotImplementedError

    def upload_subtitles(self, video_id, subtitles_id, language_code, attachment):
        """
        Upload a video subtitles file

        Args:

            video_id (str)
            subtitles_id (str)
            language_code (str)
            attachment (file object)
        """
        raise NotImplementedError

    def get_subtitles_download_url(self, video_id, subtitles_id):
        """
        TODO document
        """
        raise NotImplementedError


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

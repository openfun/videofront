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

    def transcode_video(self, video_id):
        """
        Run the transcoding job and monitor it.

        This function is an iterator on the task progress. It should periodically
        yield the progress (float value between 0 and 100).
        """
        raise NotImplementedError

    def delete_resources(self, video_id):
        """
        Delete all resources associated to a video. E.g: in case of transcoding error.
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

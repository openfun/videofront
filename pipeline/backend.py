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

from glob import glob
import os
import shutil
import subprocess

from celery import shared_task
from django.core.urlresolvers import reverse
from django.conf import settings

from pipeline.backend import BaseBackend


class Backend(BaseBackend):

    def make_file_path(self, *args):
        """
        Same as get_file_path. Create the file directory if it does not exist.
        """
        path = self.get_file_path(*args)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        return path


    @staticmethod
    def get_file_path(*args):
        """
        Get an absolute file path inside the VIDEO_STORAGE_ROOT directory.

        Args:
            *args (str): directory and file names
            create_dir (bool): if true, make sure the file directory exists
        """
        root_dir = os.path.abspath(os.path.join(settings.VIDEO_STORAGE_ROOT, 'videos'))
        path = os.path.abspath(os.path.join(root_dir, *args))

        # we check that the path is inside the VIDEO_STORAGE_ROOT/videos directory
        if not path.startswith(os.path.abspath(root_dir)):
            raise ValueError("Cannot create path {} outside of {}".format(
                path, settings.VIDEO_STORAGE_ROOT
            ))
        return path

    def _rm(self, *args):
        """
        Recursively delete a directory or file inside the video storage root.
        """
        path = self.get_file_path(*args)
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)


    ####################
    # Overridden methods
    ####################

    def upload_video(self, video_id, file_object):
        video_filename = os.path.basename(file_object.name)
        video_path = self.make_file_path(video_id, 'src', video_filename)
        copy_content(file_object, video_path)

    def delete_video(self, video_id):
        self._rm(video_id)

    def video_url(self, video_id, format_name):
        # TODO we do not include the host name?
        return reverse("storage-video", kwargs={'video_id': video_id, 'format_name': format_name})

    def upload_subtitle(self, video_id, subtitle_id, language_code, content):
        filename = "{}.{}.vtt".format(subtitle_id, language_code)
        subtitle_path = self.make_file_path(video_id, "subs", filename)
        with open(subtitle_path, "w") as out_f:
            out_f.write(content)

    def delete_subtitle(self, video_id, subtitle_id):
        for path in glob(self.get_file_path(video_id, "subs", "{}.*.vtt".format(subtitle_id))):
            os.remove(path)

    def upload_thumbnail(self, video_id, thumb_id, file_object):
        thumb_filename = "{}.jpg".format(thumb_id)
        thumb_path = self.make_file_path(video_id, 'thumbs', thumb_filename)
        copy_content(file_object, thumb_path)

    def delete_thumbnail(self, video_id, thumb_id):
        self._rm(video_id, "thumbs", "{}.jpg".format(thumb_id))

    def start_transcoding(self, video_id):
        # Note that this will trigger a KeyError if the file does not exist
        src_path = glob(self.get_file_path(video_id, "src", "*"))[0]
        for format_name, ffmpeg_settings in settings.FFMPEG_PRESETS.items():
            dst_path = self.get_file_path(video_id, '{}.mp4'.format(format_name))
            task = ffmpeg_transcode_video.delay(src_path, dst_path, ffmpeg_settings)
            import ipdb; ipdb.set_trace()
            print(task)



    ##########
    # TODO
    ##########
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

    def iter_formats(self, video_id):
        """
        Iterator on the available formats for that video. This method will be
        called after transcoding has finished.

        Yields:
            format_name (str)
            bitrate (float)
        """
        raise NotImplementedError

    def create_thumbnail(self, video_id, thumb_id):
        """
        Create a thumbnail for this video

        Args:
            video_id (str)
            thumb_id (str)
        """
        raise NotImplementedError

    def subtitle_url(self, video_id, subtitle_id, language_code):
        """
        Returns the url at which the subtitle file can be downloaded. Note
        that this method once for every subtitle object for every API videos
        API call. So the result of this result should either be fast or cached.
        """
        raise NotImplementedError

    def thumbnail_url(self, video_id, thumb_id):
        """
        Returns the url at which the video thumbnail can be downloaded. This
        should be a fast method.

        This feature is optional. If undefined, the thumbnail url will be an
        empty string.
        """
        return ''


def copy_content(file_object, path):
    """
    Copy content of file object to binary file. Write is performed chunk by
    chunk.
    """
    file_object.seek(0)
    with open(path, 'wb') as out_f:
        while True:
            chunk = file_object.read(1024)
            if not chunk:
                break
            out_f.write(chunk)

@shared_task(name='ffmpeg_transcode_video')
def ffmpeg_transcode_video(src_path, dst_path, ffmpeg_presets):
    # E.g:
    # ffmpeg -y -i src.mp4 -c:v libx264 -c:a aac -strict experimental \
    #   -r 30 -s 1280x720 -vb 5120k -ab 384k -ar 48000 dst.mp4
    command = [
        getattr(settings, 'FFMPEG_BINARY', 'ffmpeg'),
        '-y',# overwrite without asking
        '-i', src_path,# input path
        '-c:v', 'libx264',# video codec
        '-c:a', 'aac',# audio codec
        '-strict', 'experimental',# allow experimental 'aac' codec
        '-r', ffmpeg_presets.get('framerate', '30'),
        '-s', ffmpeg_presets['size'],# 16:9 video size
        '-vb', ffmpeg_presets['video_bitrate'],
        '-ab', ffmpeg_presets['audio_bitrate'],
        '-ar', ffmpeg_presets.get('audio_rate', '48000'),# audio sampling rate
        dst_path,
    ]
    # subprocess.call(command)

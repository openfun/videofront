import importlib
from io import BytesIO
import os
import shutil
import sys
import tempfile

from django.conf import settings
from django.core.urlresolvers import reverse, clear_url_caches
from django.test import TestCase
from django.test.utils import override_settings

from contrib.plugins.local import backend as local_backend
import pipeline.tasks


VIDEO_STORAGE_ROOT = tempfile.mkdtemp()


def media_path(*args):
    return os.path.join(VIDEO_STORAGE_ROOT, 'videos', *args)


@override_settings(VIDEO_STORAGE_ROOT=VIDEO_STORAGE_ROOT, BACKEND_URLS='contrib.plugins.local.urls')
class LocalBackendTests(TestCase):

    def setUp(self):
        # Create storage folder
        if os.path.exists(VIDEO_STORAGE_ROOT):
            shutil.rmtree(VIDEO_STORAGE_ROOT)
        os.makedirs(VIDEO_STORAGE_ROOT)

        # Reload project urls to make sure backend urls are loaded
        if settings.ROOT_URLCONF in sys.modules:
            importlib.reload(sys.modules[settings.ROOT_URLCONF])
        clear_url_caches()

    def tearDown(self):
        shutil.rmtree(VIDEO_STORAGE_ROOT)

    def test_attempt_to_create_directory_outside_of_video_storage_root(self):
        backend = local_backend.Backend()

        self.assertRaises(ValueError, backend.get_file_path, "../deleteme/somefile")
        self.assertRaises(ValueError, backend.make_file_path, "../deleteme/somefile")
        self.assertFalse(os.path.exists(media_path("../deleteme/somefile")))

    def test_upload_video(self):
        backend = local_backend.Backend()
        file_object = BytesIO(b"some content")
        file_object.name = "somevideo.mp4"

        backend.upload_video('videoid', file_object)

        dst_path = media_path('videoid', 'src', 'somevideo.mp4')
        self.assertTrue(os.path.exists(dst_path))
        self.assertEqual(b"some content", open(dst_path, 'rb').read())

    def test_delete_video(self):
        backend = local_backend.Backend()
        file_object = BytesIO(b"some content")
        file_object.name = "somevideo.mp4"

        backend.upload_video('videoid', file_object)
        backend.delete_video('videoid')

        dst_path = media_path('videoid', 'src', 'somevideo.mp4')
        self.assertFalse(os.path.exists(dst_path))

    def test_delete_video_does_not_fail_on_non_existing_video(self):
        backend = local_backend.Backend()
        backend.delete_video('videoid')

    def test_video_url(self):
        backend = local_backend.Backend()

        self.assertEqual("/backend/storage/videos/videoid/HD.mp4", backend.video_url("videoid", "HD"))

    def test_download_urls(self):
        url = reverse('storage-video', kwargs={'video_id': 'videoid', 'format_name': 'HD'})
        self.assertIsNotNone(url)

    def test_download_video(self):
        # Create temp video file
        directory = os.path.join(VIDEO_STORAGE_ROOT, 'videos', 'videoid')
        os.makedirs(directory)
        with open(os.path.join(directory, 'HD.mp4'), 'wb') as video_file:
            video_file.write(b"some content")

        url = reverse("storage-video", kwargs={'video_id': 'videoid', 'format_name': 'HD'})
        response = self.client.get(url)

        self.assertEqual(200, response.status_code)
        # Note that '.content' is not available because this is a streaming
        # content response
        self.assertEqual(b"some content", response.getvalue())

    @override_settings(FFMPEG_PRESETS={
        'HD': {
            'size': '1280x720',
            'video_bitrate': '5120k',
            'audio_bitrate': '384k',
        },
    })
    def test_transcode_and_download_video(self):
        backend = local_backend.Backend()
        file_object = BytesIO(b"some content")
        file_object.name = "somevideo.mp4"

        backend.upload_video('videoid', file_object)
        backend.start_transcoding('videoid')

        # Download source video file
        url = reverse("storage-video", kwargs={'video_id': 'videoid', 'format_name': 'HD'})
        response = self.client.get(url)

        self.assertEqual(200, response.status_code)
        # Note that '.content' is not available because this is a streaming
        # content response
        self.assertEqual(b"some content", response.getvalue())

    def test_upload_subtitle(self):
        backend = local_backend.Backend()

        backend.upload_subtitle("videoid", "subid", "fr", "some content")

        dst_path = media_path('videoid', 'subs', 'subid.fr.vtt')
        self.assertTrue(os.path.exists(dst_path))
        self.assertEqual("some content", open(dst_path).read())

    def test_delete_subtitle(self):
        backend = local_backend.Backend()

        backend.upload_subtitle("videoid", "subid", "fr", "some content")
        backend.delete_subtitle("videoid", "subid")

        dst_path = media_path('videoid', 'subs', 'subid.fr.vtt')
        self.assertFalse(os.path.exists(dst_path))

    @override_settings(PLUGIN_BACKEND='contrib.plugins.local.backend.Backend')
    def test_upload_subtitle_compatibility(self):
        pipeline.tasks.upload_subtitle('videoid', 'subid', 'fr', b"WEBVTT")

        dst_path = media_path('videoid', 'subs', 'subid.fr.vtt')
        self.assertTrue(os.path.exists(dst_path))
        self.assertEqual("WEBVTT", open(dst_path).read())

    def test_upload_thumbnail(self):
        backend = local_backend.Backend()
        file_object = BytesIO(b"some content")

        backend.upload_thumbnail("videoid", "thumbid", file_object)

        dst_path = media_path('videoid', 'thumbs', 'thumbid.jpg')
        self.assertTrue(os.path.exists(dst_path))
        self.assertEqual(b"some content", open(dst_path, 'rb').read())

    def test_delete_thumbnail(self):
        backend = local_backend.Backend()
        file_object = BytesIO(b"some content")

        backend.upload_thumbnail("videoid", "thumbid", file_object)
        backend.delete_thumbnail("videoid", "thumbid")

        dst_path = media_path('videoid', 'thumbs', 'thumbid.jpg')
        self.assertFalse(os.path.exists(dst_path))

from time import time

from django.test import TestCase

from pipeline import models
from pipeline.tasks import create_upload_url

from .utils import override_plugin_backend


class VideoUploadTests(TestCase):

    @override_plugin_backend(create_upload_url=lambda filename: {
        'url': 'http://example.com',
        'method': 'POST',
        'expires_at': time() + 60,
        'id': 'videoid'
    })
    def test_create_upload_url(self):
        _upload_url = create_upload_url('video.mp4')
        should_check_urls = models.VideoUploadUrl.objects.should_check()

        self.assertEqual(1, should_check_urls.count())
        url = should_check_urls.get()
        self.assertEqual('videoid', url.public_video_id)
        self.assertEqual(False, url.was_used)
        self.assertIsNone(url.last_checked)
        self.assertEqual('video.mp4', url.filename)

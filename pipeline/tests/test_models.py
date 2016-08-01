from time import time

from django.utils.timezone import now
from django.test import TestCase

from pipeline import models


class VideoUploadUrlTests(TestCase):

    def test_should_check(self):
        models.VideoUploadUrl.objects.create(
            public_video_id='available',
            expires_at=time() + 3600
        )
        models.VideoUploadUrl.objects.create(
            public_video_id='used_not_checked',
            expires_at=time() + 3600,
            was_used=True,
        )
        models.VideoUploadUrl.objects.create(
            public_video_id='almost_expired',
            expires_at=time() - 3000,
        )
        models.VideoUploadUrl.objects.create(
            public_video_id='used',
            expires_at=time() + 3600,
            was_used=True,
            last_checked=now()
        )
        models.VideoUploadUrl.objects.create(
            public_video_id='expired',
            expires_at=time() - 3600,
            last_checked=now()
        )

        should_check_video_ids = [u.public_video_id for u in models.VideoUploadUrl.objects.should_check()]

        self.assertIn('available', should_check_video_ids)
        self.assertIn('almost_expired', should_check_video_ids)
        self.assertIn('used_not_checked', should_check_video_ids)
        self.assertNotIn('used', should_check_video_ids)
        self.assertNotIn('expired', should_check_video_ids)

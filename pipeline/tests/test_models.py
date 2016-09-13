from time import time

from django.test import TestCase

from pipeline import models
from pipeline.tests import factories


class VideoUploadUrlTests(TestCase):

    def test_available(self):
        factories.VideoUploadUrlFactory(
            public_video_id='available',
            expires_at=time() + 3600
        )
        factories.VideoUploadUrlFactory(
            public_video_id='almost_expired',
            expires_at=time() - 3000,
        )
        factories.VideoUploadUrlFactory(
            public_video_id='used',
            expires_at=time() + 3600,
            was_used=True,
        )
        factories.VideoUploadUrlFactory(
            public_video_id='expired',
            expires_at=time() - 3600,
        )

        available_video_ids = [u.public_video_id for u in models.VideoUploadUrl.objects.available()]

        self.assertIn('available', available_video_ids)
        self.assertIn('almost_expired', available_video_ids)
        self.assertNotIn('used', available_video_ids)
        self.assertNotIn('expired', available_video_ids)

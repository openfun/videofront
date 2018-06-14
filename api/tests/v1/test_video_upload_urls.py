from io import StringIO
from time import time
from unittest.mock import Mock

from django.urls import reverse

from pipeline import models
from pipeline.tests import factories
from pipeline.tests.utils import override_plugin_backend

from .base import BaseAuthenticatedTests


class VideoUploadUrlTests(BaseAuthenticatedTests):
    def test_create_videouploadurl(self):
        url = reverse("api:v1:videouploadurl-list")

        response = self.client.post(url)

        self.assertEqual(201, response.status_code)
        upload_url = response.json()
        self.assertIn("id", upload_url)
        self.assertEqual(1, models.VideoUploadUrl.objects.count())
        self.assertEqual(self.user, models.VideoUploadUrl.objects.get().owner)
        self.assertIsNone(models.VideoUploadUrl.objects.get().playlist)

    def test_create_video_upload_url_with_origin(self):
        response = self.client.post(
            reverse("api:v1:videouploadurl-list"), data={"origin": "example.com"}
        )

        self.assertEqual(201, response.status_code)
        upload_url = response.json()
        self.assertIn("origin", upload_url)

    def test_list_videouploadurls(self):
        url = reverse("api:v1:videouploadurl-list")
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.json())

    def test_used_upload_urls_are_not_listed(self):
        factories.VideoUploadUrlFactory(
            public_video_id="unused",
            owner=self.user,
            expires_at=time() + 3600,
            was_used=False,
        )
        factories.VideoUploadUrlFactory(
            public_video_id="used",
            owner=self.user,
            expires_at=time() + 3600,
            was_used=True,
        )
        url = reverse("api:v1:videouploadurl-list")
        response = self.client.get(url)

        self.assertEqual(1, len(response.json()))
        self.assertEqual("unused", response.json()[0]["id"])

    def test_create_videouploadurl_with_playlist(self):
        playlist = factories.PlaylistFactory(owner=self.user)
        response = self.client.post(
            reverse("api:v1:videouploadurl-list"), {"playlist": playlist.public_id}
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual(playlist, models.VideoUploadUrl.objects.get().playlist)

    def test_obtain_video_upload_url_with_invalid_playlist_id(self):
        response = self.client.post(
            reverse("api:v1:videouploadurl-list"), {"playlist": "dummy_id"}
        )

        self.assertEqual(400, response.status_code)

    def test_obtain_video_upload_url_with_unauthorized_playlist_id(self):
        # Create factory from different owner
        playlist = factories.PlaylistFactory()

        response = self.client.post(
            reverse("api:v1:videouploadurl-list"), {"playlist": playlist.public_id}
        )

        self.assertNotEqual(self.user, playlist.owner)
        self.assertEqual(400, response.status_code)

    def test_send_file_to_upload_url(self):
        self.client.logout()  # upload should work even for non logged-in clients
        video_upload_url = factories.VideoUploadUrlFactory(
            public_video_id="videoid",
            owner=self.user,
            expires_at=time() + 3600,
            origin="example.com",
        )
        video_file = StringIO("some video content")

        upload_video = Mock()
        start_transcoding = Mock(return_value=[])
        create_thumbnail = Mock()
        with override_plugin_backend(
            upload_video=upload_video,
            start_transcoding=start_transcoding,
            iter_formats=Mock(return_value=[]),
            create_thumbnail=create_thumbnail,
        ):
            response = self.client.post(
                reverse(
                    "api:v1:video-upload",
                    kwargs={"video_id": video_upload_url.public_video_id},
                ),
                {"name": "video.mp4", "file": video_file},
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("example.com", response["Access-Control-Allow-Origin"])
        upload_video.assert_called_once()
        create_thumbnail.assert_called_once()
        start_transcoding.assert_called_once_with("videoid")
        self.assertEqual("videoid", response.json()["id"])

    def test_send_empty_file_to_upload_url(self):
        video_upload_url = factories.VideoUploadUrlFactory(
            public_video_id="videoid",
            owner=self.user,
            expires_at=time() + 3600,
            origin="*",
        )
        response = self.client.post(
            reverse(
                "api:v1:video-upload",
                kwargs={"video_id": video_upload_url.public_video_id},
            ),
            {"name": "video.mp4", "file": StringIO("")},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual("*", response["Access-Control-Allow-Origin"])
        self.assertIn("file", response.json())

    def test_send_file_to_expired_upload_url(self):
        video_upload_url = factories.VideoUploadUrlFactory(
            public_video_id="videoid",
            owner=self.user,
            expires_at=time() - 7200,
            origin="*",
        )
        video_file = StringIO("some video content")

        response = self.client.post(
            reverse(
                "api:v1:video-upload",
                kwargs={"video_id": video_upload_url.public_video_id},
            ),
            {"name": "video.mp4", "file": video_file},
        )

        self.assertEqual(404, response.status_code)
        self.assertNotIn("Access-Control-Allow-Origin", response)

    def test_OPTIONS_on_upload_url(self):
        self.client.logout()  # upload should work even for non logged-in clients
        video_upload_url = factories.VideoUploadUrlFactory(
            public_video_id="videoid",
            owner=self.user,
            expires_at=time() + 3600,
            origin="*",
        )
        response = self.client.options(
            reverse(
                "api:v1:video-upload",
                kwargs={"video_id": video_upload_url.public_video_id},
            )
        )

        self.assertEqual(200, response.status_code)
        self.assertIn("Access-Control-Allow-Origin", response)
        self.assertEqual("*", response["Access-Control-Allow-Origin"])

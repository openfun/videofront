import json
from io import BytesIO
from time import time

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import datetime, get_current_timezone

from mock import Mock, patch

from pipeline import models
from pipeline.tests import factories
from pipeline.tests.utils import override_plugin_backend

from .base import BaseAuthenticatedTests


class VideosUnauthenticatedTests(TestCase):
    def test_list_videos(self):
        url = reverse("api:v1:video-list")
        response = self.client.get(url)
        # BasicAuthentication returns a 401 in case
        self.assertEqual(401, response.status_code)


# Moving the cache to memory is required to obtain an accurate count of the number of SQL queries
@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class VideosTests(BaseAuthenticatedTests):

    # queries:
    # 1) django session
    # 2) user authentication
    VIDEOS_LIST_NUM_QUERIES_AUTH = 2
    # 3) video + transcoding job
    VIDEOS_LIST_NUM_QUERIES_EMPTY_RESULT = VIDEOS_LIST_NUM_QUERIES_AUTH + 1
    # 4) subtitles prefetch
    # 5) formats prefetch
    VIDEOS_LIST_NUM_QUERIES = VIDEOS_LIST_NUM_QUERIES_EMPTY_RESULT + 2

    def test_list_videos(self):
        url = reverse("api:v1:video-list")
        with self.assertNumQueries(self.VIDEOS_LIST_NUM_QUERIES_EMPTY_RESULT):
            response = self.client.get(url)
        videos = response.json()

        self.assertEqual(200, response.status_code)
        self.assertEqual([], videos)

    def test_list_videos_with_different_owners(self):
        video1 = factories.VideoFactory(owner=self.user)
        factories.VideoFactory(owner=factories.UserFactory())
        videos = self.client.get(reverse("api:v1:video-list")).json()

        self.assertEqual(1, len(videos))
        self.assertEqual(video1.public_id, videos[0]["id"])

    def test_get_video(self):
        video = factories.VideoFactory(
            public_id="videoid", title="Some title", owner=self.user
        )
        video.processing_state.status = models.ProcessingState.STATUS_SUCCESS
        video.processing_state.save()
        response = self.client.get(
            reverse("api:v1:video-detail", kwargs={"id": "videoid"})
        )
        self.assertEqual(200, response.status_code)
        video = response.json()

        self.assertEqual("videoid", video["id"])
        self.assertEqual("Some title", video["title"])
        self.assertEqual([], video["subtitles"])
        self.assertEqual([], video["formats"])
        self.assertEqual("success", video["processing"]["status"])

    def test_get_video_processing_state_started_at_truncated_microseconds(self):
        factories.VideoFactory(public_id="videoid", title="Some title", owner=self.user)
        started_at = datetime(2016, 1, 1, 12, 13, 14, 1516, get_current_timezone())
        models.ProcessingState.objects.filter(video__public_id="videoid").update(
            started_at=started_at
        )

        response = self.client.get(
            reverse("api:v1:video-detail", kwargs={"id": "videoid"})
        )
        video = response.json()

        # Check that microseconds are truncated
        self.assertEqual("2016-01-01T12:13:14Z", video["processing"]["started_at"])

    def test_get_not_processing_video(self):
        factories.VideoFactory(public_id="videoid", title="videotitle", owner=self.user)
        url = reverse("api:v1:video-list")
        videos = self.client.get(url).json()

        self.assertEqual(1, len(videos))
        self.assertEqual("videoid", videos[0]["id"])
        self.assertEqual("videotitle", videos[0]["title"])
        self.assertIn("processing", videos[0])
        self.assertIsNotNone(videos[0]["processing"])
        self.assertEqual("pending", videos[0]["processing"]["status"])

    def test_get_processing_video(self):
        video = factories.VideoFactory(
            public_id="videoid", title="videotitle", owner=self.user
        )
        video.processing_state.progress = 42
        video.processing_state.status = models.ProcessingState.STATUS_PROCESSING
        video.processing_state.save()
        videos = self.client.get(reverse("api:v1:video-list")).json()

        self.assertEqual("processing", videos[0]["processing"]["status"])
        self.assertEqual(42, videos[0]["processing"]["progress"])

    def test_get_failed_video(self):
        video = factories.VideoFactory(
            public_id="videoid", title="videotitle", owner=self.user
        )
        video.processing_state.status = models.ProcessingState.STATUS_FAILED
        video.processing_state.save()

        response_detail = self.client.get(
            reverse("api:v1:video-detail", kwargs={"id": "videoid"})
        )
        response_list = self.client.get(reverse("api:v1:video-list"))

        self.assertEqual(200, response_detail.status_code)
        self.assertEqual(200, response_list.status_code)
        self.assertEqual([], response_list.json())

    def test_get_video_with_cache(self):
        factories.VideoFactory(public_id="videoid", title="Some title", owner=self.user)
        with self.assertNumQueries(self.VIDEOS_LIST_NUM_QUERIES):
            response1 = self.client.get(
                reverse("api:v1:video-detail", kwargs={"id": "videoid"})
            )
        with self.assertNumQueries(self.VIDEOS_LIST_NUM_QUERIES_AUTH):
            response2 = self.client.get(
                reverse("api:v1:video-detail", kwargs={"id": "videoid"})
            )

        self.assertEqual(200, response1.status_code)
        self.assertEqual(200, response2.status_code)

    def test_list_failed_videos(self):
        video = factories.VideoFactory(
            public_id="videoid", title="videotitle", owner=self.user
        )
        video.processing_state.status = models.ProcessingState.STATUS_FAILED
        video.processing_state.save()

        videos = self.client.get(reverse("api:v1:video-list")).json()
        self.assertEqual([], videos)

    def test_create_video_fails(self):
        url = reverse("api:v1:video-list")
        response = self.client.post(url, {"public_id": "videoid", "title": "sometitle"})
        self.assertEqual(405, response.status_code)  # method not allowed

    @override_plugin_backend(
        start_transcoding=lambda video_id: [], iter_formats=lambda video_id: []
    )
    def test_get_video_that_was_just_uploaded(self):
        factories.VideoUploadUrlFactory(
            public_video_id="videoid", expires_at=time() + 3600, owner=self.user
        )
        response = self.client.get(
            reverse("api:v1:video-detail", kwargs={"id": "videoid"})
        )

        self.assertEqual(200, response.status_code)

    def test_update_video_title(self):
        factories.VideoFactory(public_id="videoid", title="videotitle", owner=self.user)
        response = self.client.put(
            reverse("api:v1:video-detail", kwargs={"id": "videoid"}),
            data=json.dumps({"title": "title2"}),
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("title2", models.Video.objects.get().title)

    def test_delete_video(self):
        mock_delete_video = Mock()
        factories.VideoFactory(public_id="videoid", owner=self.user)
        with override_plugin_backend(delete_video=mock_delete_video):
            response = self.client.delete(
                reverse("api:v1:video-detail", kwargs={"id": "videoid"})
            )

        self.assertEqual(204, response.status_code)
        self.assertEqual(0, models.Video.objects.count())
        mock_delete_video.assert_called_once_with("videoid")

    @override_plugin_backend(
        subtitle_url=lambda vid, sid, lang: "http://example.com/{}.vtt".format(sid)
    )
    def test_get_video_with_subtitles(self):
        video = factories.VideoFactory(public_id="videoid", owner=self.user)
        video.subtitles.create(language="fr", public_id="subid1")
        video.subtitles.create(language="en", public_id="subid2")

        with self.assertNumQueries(self.VIDEOS_LIST_NUM_QUERIES):
            video = self.client.get(
                reverse("api:v1:video-detail", kwargs={"id": "videoid"})
            ).json()

        self.assertEqual(
            [
                {
                    "id": "subid1",
                    "language": "fr",
                    "url": "http://example.com/subid1.vtt",
                },
                {
                    "id": "subid2",
                    "language": "en",
                    "url": "http://example.com/subid2.vtt",
                },
            ],
            video["subtitles"],
        )

    @override_plugin_backend(
        video_url=lambda video_id, format_name: "http://example.com/{}/{}.mp4".format(
            video_id, format_name
        ),
        iter_formats=lambda video_id: [],
    )
    def test_get_video_with_formats(self):
        video = factories.VideoFactory(public_id="videoid", owner=self.user)
        video.formats.create(name="SD", bitrate=128)
        video.formats.create(name="HD", bitrate=256)

        with self.assertNumQueries(self.VIDEOS_LIST_NUM_QUERIES):
            video = self.client.get(
                reverse("api:v1:video-detail", kwargs={"id": "videoid"})
            ).json()

        self.assertEqual(
            [
                {
                    "name": "SD",
                    "url": "http://example.com/videoid/SD.mp4",
                    "bitrate": 128.0,
                },
                {
                    "name": "HD",
                    "url": "http://example.com/videoid/HD.mp4",
                    "bitrate": 256.0,
                },
            ],
            video["formats"],
        )

    def test_list_videos_in_playlist(self):
        playlist = factories.PlaylistFactory(
            name="Funkadelic playlist", owner=self.user
        )
        # Create a video attached to a playlist
        video_in_playlist = factories.VideoFactory(owner=self.user)
        playlist.videos.add(video_in_playlist)
        # Create a video not attached to a playlist
        factories.VideoFactory(owner=self.user)

        response = self.client.get(
            reverse("api:v1:video-list"), data={"playlist_id": playlist.public_id}
        )
        videos = response.json()

        self.assertEqual(1, len(videos))
        self.assertEqual(video_in_playlist.public_id, videos[0]["id"])

    @override_plugin_backend(
        thumbnail_url=lambda video_id, thumb_id: "http://imgur.com/{}/thumbs/{}.jpg".format(
            video_id, thumb_id
        )
    )
    def test_get_video_thumbnail(self):
        factories.VideoFactory(
            public_id="videoid", owner=self.user, public_thumbnail_id="thumbid"
        )
        video = self.client.get(
            reverse("api:v1:video-detail", kwargs={"id": "videoid"})
        ).json()
        self.assertIn("thumbnail", video)
        self.assertEqual(
            "http://imgur.com/videoid/thumbs/thumbid.jpg", video["thumbnail"]
        )

    @patch("pipeline.utils.resize_image")
    @override_plugin_backend(
        upload_thumbnail=lambda video_id, thumb_id, file_object: None,
        delete_thumbnail=lambda video_id, thumb_id: None,
        thumbnail_url=lambda video_id, thumb_id: "http://example.com/{}/{}.jpg".format(
            video_id, thumb_id
        ),
    )
    def test_upload_video_thumbnail(self, mock_resize_image):
        video = factories.VideoFactory(public_id="videoid", owner=self.user)
        old_thumbnail_url = video.thumbnail_url
        url = reverse("api:v1:video-thumbnail", kwargs={"id": "videoid"})
        thumb_file = BytesIO(b"thumb content")
        thumb_file.name = "thumb.jpg"
        response = self.client.post(url, {"name": "thumb.jpg", "file": thumb_file})

        self.assertEqual(200, response.status_code)
        self.assertIn("thumbnail", response.json())
        self.assertIn("http://example.com/videoid", response.json()["thumbnail"])
        self.assertNotEqual(old_thumbnail_url, response.json()["thumbnail"])

    def test_upload_invalid_video_thumbnail(self):
        factories.VideoFactory(public_id="videoid", owner=self.user)
        url = reverse("api:v1:video-thumbnail", kwargs={"id": "videoid"})
        thumb_file = BytesIO(b"invalid thumb content")
        thumb_file.name = "thumb.jpg"
        response = self.client.post(url, {"name": "thumb.jpg", "file": thumb_file})

        self.assertEqual(400, response.status_code)
        self.assertIn("file", response.json())

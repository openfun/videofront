from __future__ import unicode_literals

from io import StringIO

from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from mock import Mock, patch

from pipeline import models
from pipeline.tests import factories
from pipeline.tests.utils import override_plugin_backend

from .base import BaseAuthenticatedTests


class SubtitleTests(BaseAuthenticatedTests):
    SRT_CONTENT = """1
00:00:00,822 --> 00:00:01,565
Hello world!

2
00:00:01,840 --> 00:00:03,280
My name is VIDEOFRONT and I am awesome.

3
00:00:03,920 --> 00:00:08,250
Also I have utf8 characters: é û ë ï 你好."""

    @override_plugin_backend(
        upload_subtitle=lambda *args: None,
        subtitle_url=lambda *args: "http://example.com/sub.vtt",
    )
    def test_upload_subtitle(self):
        video = factories.VideoFactory(public_id="videoid", owner=self.user)
        url = reverse("api:v1:video-subtitles", kwargs={"id": "videoid"})
        subfile = StringIO(self.SRT_CONTENT)
        response = self.client.post(
            url, data={"language": "fr", "name": "sub.srt", "file": subfile}
        )

        self.assertEqual(201, response.status_code)
        subtitle = response.json()
        self.assertLess(0, len(subtitle["id"]))
        self.assertEqual("fr", subtitle["language"])
        self.assertEqual("http://example.com/sub.vtt", subtitle["url"])
        self.assertEqual(1, video.subtitles.count())

    def test_upload_subtitle_invalid_language(self):
        factories.VideoFactory(public_id="videoid", owner=self.user)
        url = reverse("api:v1:video-subtitles", kwargs={"id": "videoid"})
        # only country codes are accepted
        response = self.client.post(url, data={"language": "french"})

        self.assertEqual(400, response.status_code)
        self.assertIn("language", response.json())
        self.assertEqual(0, models.Subtitle.objects.count())

    def test_upload_subtitle_missing_file(self):
        factories.VideoFactory(public_id="videoid", owner=self.user)
        url = reverse("api:v1:video-subtitles", kwargs={"id": "videoid"})
        response = self.client.post(url, data={"language": "fr"})

        self.assertEqual(400, response.status_code)
        self.assertIn("file", response.json())
        self.assertEqual(0, models.Subtitle.objects.count())

    @patch("django.core.handlers.base.logger")  # mute request logger
    def test_upload_subtitle_failed_upload(self, mock_logger):
        factories.VideoFactory(public_id="videoid", owner=self.user)
        url = reverse("api:v1:video-subtitles", kwargs={"id": "videoid"})
        subfile = StringIO(self.SRT_CONTENT)

        upload_subtitle = Mock(side_effect=ValueError)
        with override_plugin_backend(upload_subtitle=upload_subtitle):
            self.assertRaises(
                ValueError,
                self.client.post,
                url,
                data={"language": "fr", "name": "sub.srt", "file": subfile},
            )

        self.assertEqual(0, models.Subtitle.objects.count())

    def test_cannot_modify_subtitle(self):
        video = factories.VideoFactory(public_id="videoid", owner=self.user)
        video.subtitles.create(public_id="subid", language="fr")
        url = reverse("api:v1:video-subtitles", kwargs={"id": "videoid"})
        subfile = StringIO(self.SRT_CONTENT)

        with override_plugin_backend(
            upload_subtitle=lambda *args: None, subtitle_url=lambda *args: None
        ):
            response = self.client.post(
                url,
                data={
                    "id": "subid",
                    "language": "en",
                    "name": "sub.srt",
                    "file": subfile,
                },
            )

        # Subtitle is in fact created, not modified
        self.assertEqual(201, response.status_code)
        self.assertEqual("fr", video.subtitles.get(public_id="subid").language)
        self.assertEqual(
            "en", video.subtitles.exclude(public_id="subid").get().language
        )

    @override_settings(SUBTITLES_MAX_BYTES=139)
    def test_upload_subtitle_too_large(self):
        factories.VideoFactory(public_id="videoid", owner=self.user)
        content = (
            "Some vtt content here. This should as long as a tweet, at"
            " 140 characters exactly. Yes, I counted, multiple times and came up with"
            " 140 chars."
        )
        subfile = StringIO(content)
        self.assertEqual(140, len(content))
        url = reverse("api:v1:video-subtitles", kwargs={"id": "videoid"})

        response = self.client.post(
            url, data={"language": "en", "name": "sub.srt", "file": subfile}
        )
        self.assertEqual(400, response.status_code)
        self.assertIn("file", response.json())
        self.assertIn("139", response.json()["file"])

    def test_upload_subtitle_invalid_format(self):
        factories.VideoFactory(public_id="videoid", owner=self.user)
        subfile = StringIO("Some invalid content here.")
        response = self.client.post(
            reverse("api:v1:video-subtitles", kwargs={"id": "videoid"}),
            data={"language": "en", "name": "sub.srt", "file": subfile},
        )
        self.assertEqual(400, response.status_code)
        self.assertIn("file", response.json())
        self.assertEqual("Could not detect subtitle format", response.json()["file"])
        self.assertEqual(0, models.Subtitle.objects.count())

    def test_get_subtitle(self):
        video = factories.VideoFactory(public_id="videoid", owner=self.user)
        factories.SubtitleFactory(video=video, public_id="subid", language="fr")

        with override_plugin_backend(subtitle_url=lambda *args: "http://sub.vtt"):
            response = self.client.get(
                reverse("api:v1:subtitle-detail", kwargs={"id": "subid"})
            )

        self.assertEqual(200, response.status_code)
        subtitle = response.json()
        self.assertEqual("fr", subtitle["language"])
        self.assertEqual("subid", subtitle["id"])
        self.assertEqual("http://sub.vtt", subtitle["url"])

    def test_delete_subtitle(self):
        video = factories.VideoFactory(public_id="videoid", owner=self.user)
        factories.SubtitleFactory(video=video, public_id="subid", language="fr")

        mock_backend = Mock(return_value=Mock(delete_subtitle=Mock()))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            response = self.client.delete(
                reverse("api:v1:subtitle-detail", kwargs={"id": "subid"})
            )

        self.assertEqual(204, response.status_code)
        self.assertEqual(0, models.Subtitle.objects.count())
        mock_backend.return_value.delete_subtitle.assert_called_once_with(
            "videoid", "subid"
        )

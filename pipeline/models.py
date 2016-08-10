from django.conf.global_settings import LANGUAGES
from django.core.validators import MinLengthValidator, MinValueValidator, MaxValueValidator
from django.db import models

from . import backend
from . import managers


class Video(models.Model):
    title = models.CharField(max_length=100)
    public_id = models.CharField(
        max_length=20, unique=True,
        validators=[MinLengthValidator(1)]
    )

    @property
    def transcoding_status(self):
        return self.transcoding.status if self.transcoding else None

    @property
    def transcoding_progress(self):
        return self.transcoding.progress if self.transcoding else None

    @property
    def transcoding_started_at(self):
        return self.transcoding.started_at if self.transcoding else None


class VideoUploadUrl(models.Model):
    """
    Video upload urls are generated in order to upload new videos. To each url is
    associated an expiration date after which is cannot be used. Note however
    that an upload that has started just before the expiry date should proceed
    normally.
    """
    public_video_id = models.CharField(
        max_length=20,
        unique=True,
        validators=[MinLengthValidator(1)]
    )
    filename = models.CharField(
        verbose_name="Uploaded file name",
        max_length=128,
    )
    expires_at = models.IntegerField(
        verbose_name="Timestamp at which the url expires",
        db_index=True
    )
    was_used = models.BooleanField(
        verbose_name="Was the upload url used?",
        default=False,
        db_index=True
    )
    last_checked = models.DateTimeField(
        verbose_name="Last time it was checked if the url was used",
        blank=True, null=True,
        db_index=True,
    )

    objects = managers.VideoUploadUrlManager()


class VideoTranscoding(models.Model):

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_FAILED = 'failed'
    STATUS_SUCCESS = 'success'
    STATUSES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_SUCCESS, 'Success'),
    )

    video = models.OneToOneField(Video, related_name='transcoding')
    started_at = models.DateTimeField(
        verbose_name="Time of transcoding job start",
        auto_now=True
    )
    progress = models.FloatField(
        verbose_name="Progress percentage",
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    status = models.CharField(
        verbose_name="Status",
        max_length=32,
        choices=STATUSES
    )
    message = models.CharField(max_length=1024, blank=True)


class VideoSubtitles(models.Model):

    video = models.ForeignKey(Video, related_name='subtitles')
    public_id = models.CharField(
        max_length=20, unique=True,
        validators=[MinLengthValidator(1)]
    )
    language = models.CharField(
        max_length=3,
        choices=LANGUAGES
    )


class VideoFormat(models.Model):

    video = models.ForeignKey(Video, related_name='formats')
    name = models.CharField(max_length=128)
    bitrate = models.FloatField(validators=[MinValueValidator(0)])

    @property
    def streaming_url(self):
        return backend.get().get_video_streaming_url(self.video.public_id, self.name)

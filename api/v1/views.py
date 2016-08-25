from time import sleep

from django.conf import settings
from django.db import transaction
from django.http import Http404
import django_filters
from rest_framework.exceptions import ValidationError
from rest_framework import filters
from rest_framework import mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.decorators import detail_route
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from pipeline import exceptions
from pipeline import models
from pipeline import tasks
from . import serializers


AUTHENTICATION_CLASSES = (BasicAuthentication, SessionAuthentication, TokenAuthentication)
PERMISSION_CLASSES = (IsAuthenticated,)


class PlaylistFilter(filters.FilterSet):
    """
    Filter playlists by name.
    """
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = models.Playlist
        fields = ['name']


class PlaylistViewSet(viewsets.ModelViewSet):
    """
    List, update and create video playlists.
    """
    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = PERMISSION_CLASSES

    serializer_class = serializers.PlaylistSerializer

    lookup_field = 'public_id'
    lookup_url_kwarg = 'id'

    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = PlaylistFilter

    def get_queryset(self):
        return models.Playlist.objects.filter(owner=self.request.user)


class VideoFilter(filters.FilterSet):
    """
    Filter videos by playlist public id.
    """
    playlist_id = django_filters.CharFilter(name="playlists", lookup_expr="public_id")

    class Meta:
        model = models.Video
        fields = ['playlist_id']


class VideoViewSet(mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    """
    List available videos. Note that you may obtain only the videos that belong
    to a certain playlist by passing the argument `?playlist_id=xxxx`.
    """
    # Similar to a generic model viewset, but without creation features. Video
    # creation is only available through upload.

    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = PERMISSION_CLASSES

    serializer_class = serializers.VideoSerializer

    lookup_field = 'public_id'
    lookup_url_kwarg = 'id'

    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = VideoFilter


    def get_queryset(self):
        queryset = models.Video.objects.select_related(
            'processing_state'
        ).prefetch_related(
            'subtitles', 'formats'
        ).exclude(
            processing_state__status=models.ProcessingState.STATUS_FAILED
        ).filter(
           owner=self.request.user
        )

        return queryset

    def get_object(self):
        try:
            return super(VideoViewSet, self).get_object()
        except Http404:
            # Force a delay in order to avoid API flooding. This is necessary
            # to avoid rate limiting by exterior API. It could probably be
            # implemented differently (for instance: with django REST
            # framework's UserRateThrottle) but this is the most effective
            # solution to date.
            sleep(0.1)

            # Check if the video was not just uploaded and try again
            video_public_id = self.kwargs[self.lookup_url_kwarg or self.lookup_field]
            tasks.monitor_uploads([video_public_id])
            return super(VideoViewSet, self).get_object()

    def perform_destroy(self, instance):
        # Delete external resources
        super(VideoViewSet, self).perform_destroy(instance)
        tasks.delete_video(instance.public_id)

    @detail_route(methods=['POST'])
    def subtitles(self, request, **kwargs):
        """
        Subtitle upload

        The subtitle file must be added as an "attachment" file object.
        """
        video = self.get_object()
        serializer = serializers.SubtitleSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        attachment = request.FILES.get("attachment")

        if not attachment:
            return Response({'attachment': "Missing attachment"}, status=status.HTTP_400_BAD_REQUEST)
        if attachment.size > settings.SUBTITLES_MAX_BYTES:
            return Response(
                {
                    'attachment': "Attachment too large. Maximum allowed size: {} bytes".format(
                        settings.SUBTITLES_MAX_BYTES
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # We do this in an atomic transaction to avoid creating db object in
            # case of upload failure
            with transaction.atomic():
                subtitle = serializer.save(video_id=video.id)
                tasks.upload_subtitle(video.public_id, subtitle.public_id, subtitle.language, attachment.read())
        except exceptions.SubtitleInvalid as e:
            return Response({'attachment': e.args[0]}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VideoUploadViewSet(viewsets.ViewSet):
    """
    Generate video upload urls.
    """
    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = PERMISSION_CLASSES

    def create(self, request):
        filename = request.data.get('filename')
        if not filename:
            raise ValidationError("Missing filename parameter")
        if len(filename) > 128:
            raise ValidationError("Invalid filename parameter (> 128 characters)")

        # Validate playlist id. Note that this could be in a serializer, but I
        # have not found a proper way to do it.
        playlist_public_id = request.data.get('playlist_id')
        if playlist_public_id is not None:
            try:
                models.Playlist.objects.get(owner=request.user, public_id=playlist_public_id)
            except models.Playlist.DoesNotExist:
                return Response({'playlist_id': "Does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        url_info = tasks.get_upload_url(request.user.id, filename, playlist_public_id=playlist_public_id)
        return Response(url_info)


class SubtitleViewSet(mixins.RetrieveModelMixin,
                      mixins.DestroyModelMixin,
                      viewsets.GenericViewSet):
    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = PERMISSION_CLASSES

    serializer_class = serializers.SubtitleSerializer

    lookup_field = 'public_id'
    lookup_url_kwarg = 'id'


    def get_queryset(self):
        queryset = models.Subtitle.objects.select_related(
            'video'
        ).exclude(
            video__processing_state__status=models.ProcessingState.STATUS_FAILED
        ).filter(
           video__owner=self.request.user
        )
        return queryset

    def perform_destroy(self, instance):
        super(SubtitleViewSet, self).perform_destroy(instance)
        tasks.delete_subtitle(instance.video.public_id, instance.public_id)

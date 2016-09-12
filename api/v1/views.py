from time import sleep

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.http import Http404
import django_filters
from rest_framework.exceptions import ValidationError
from rest_framework import filters
from rest_framework import mixins
from rest_framework import status as rest_status
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.decorators import detail_route
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from pipeline import cache
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


    @detail_route(methods=['POST'])
    def add_video(self, request, **kwargs):
        """
        Add a video to a playlist

        Note that a user may only manage playlist videos for videos and playlists he owns.
        """
        try:
            playlist, video = self._get_playlist_video(request, **kwargs)
        except ErrorResponse as e:
            return e.response
        playlist.videos.add(video)
        return Response({}, status=rest_status.HTTP_204_NO_CONTENT)

    @detail_route(methods=['POST'])
    def remove_video(self, request, **kwargs):
        """
        Remove a video from a playlist

        Note that a user may only manage playlist videos for videos and playlists he owns.
        """
        try:
            playlist, video = self._get_playlist_video(request, **kwargs)
        except ErrorResponse as e:
            return e.response
        playlist.videos.remove(video)
        return Response({}, status=rest_status.HTTP_204_NO_CONTENT)

    def _get_playlist_video(self, request, **kwargs):
        """
        Get the playlist and video objects associated to a call to add_video or remove_video

        Returns:
            playlist (models.Playlist)
            video (models.Video)

        Raise:
            ErrorResponse
        """
        playlist = self.get_object()
        serializer = serializers.SubtitleSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        public_video_id = request.data.get("id")

        if not public_video_id:
            raise ErrorResponse({'id': "Missing argument"}, status=rest_status.HTTP_400_BAD_REQUEST)

        try:
            video = models.Video.objects.filter(
                owner=request.user
            ).exclude(
                processing_state__status=models.ProcessingState.STATUS_FAILED
            ).get(public_id=public_video_id)
        except models.Video.DoesNotExist:
            raise ErrorResponse({'id': "Video does not exist"}, status=rest_status.HTTP_404_NOT_FOUND)

        return playlist, video


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


class UserViewSet(mixins.RetrieveModelMixin,
                  mixins.CreateModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    """
    User creation, listing and details. Note that this viewset is only
    accessible to admin (staff) users.
    """

    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = (IsAuthenticated, IsAdminUser)

    queryset = User.objects.all().order_by('-date_joined').select_related('auth_token')
    serializer_class = serializers.UserSerializer

    lookup_field = 'username'
    lookup_url_kwarg = 'username'

    class Meta:
        model = User


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

    def retrieve(self, request, *args, **kwargs):
        # We override the `retrieve` method in order to cache API results for
        # /video/<videoid> calls.
        public_video_id = self.kwargs[self.lookup_url_kwarg or self.lookup_field]
        response_data = cache.get(public_video_id)
        if response_data is None:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            response_data = serializer.data
            cache.set(public_video_id, response_data)
        return Response(response_data)

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
            public_video_id = self.kwargs[self.lookup_url_kwarg or self.lookup_field]
            tasks.monitor_upload(public_video_id, wait=True)
            return super(VideoViewSet, self).get_object()

    def perform_destroy(self, instance):
        # Delete external resources
        super(VideoViewSet, self).perform_destroy(instance)
        tasks.delete_video(instance.public_id)

    @detail_route(methods=['POST'])
    def subtitles(self, request, **kwargs):
        """
        Subtitle upload

        The subtitle file must be added as a "file" file object.
        """
        video = self.get_object()
        serializer = serializers.SubtitleSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        attachment = request.FILES.get("file")

        if not attachment:
            return Response({'file': "Missing file"}, status=rest_status.HTTP_400_BAD_REQUEST)
        if attachment.size > settings.SUBTITLES_MAX_BYTES:
            return Response(
                {
                    'file': "File too large. Maximum allowed size: {} bytes".format(
                        settings.SUBTITLES_MAX_BYTES
                    )
                },
                status=rest_status.HTTP_400_BAD_REQUEST
            )

        try:
            # We do this in an atomic transaction to avoid creating db object in
            # case of upload failure
            with transaction.atomic():
                subtitle = serializer.save(video_id=video.id)
                tasks.upload_subtitle(video.public_id, subtitle.public_id, subtitle.language, attachment.read())
        except exceptions.SubtitleInvalid as e:
            return Response({'file': e.args[0]}, status=rest_status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data, status=rest_status.HTTP_201_CREATED)


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
                return Response({'playlist_id': "Does not exist"}, status=rest_status.HTTP_400_BAD_REQUEST)

        url_info = tasks.get_upload_url(request.user.id, filename, playlist_public_id=playlist_public_id)
        return Response(url_info)


class ErrorResponse(Exception):
    def __init__(self, response_data, status=None):
        super(ErrorResponse, self).__init__(response_data, status)
        self.response_data = response_data
        self.status = status

    @property
    def response(self):
        return Response(self.response_data, status=self.status)

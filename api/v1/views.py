from time import sleep
from django.http import Http404
from rest_framework import exceptions
from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from pipeline import models
from pipeline import tasks
from . import serializers


AUTHENTICATION_CLASSES = (BasicAuthentication, SessionAuthentication, TokenAuthentication)
PERMISSION_CLASSES = (IsAuthenticated,)



class VideoViewSet(mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    """
    List available videos.
    """
    # Similar to a generic model viewset, but without creation features. Video
    # creation is only available through upload.

    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = PERMISSION_CLASSES

    queryset = models.Video.objects.select_related(
        'transcoding'
    ).prefetch_related(
        'subtitles', 'formats'
    ).exclude(
        transcoding__status=models.VideoTranscoding.STATUS_FAILED
    )
    serializer_class = serializers.VideoSerializer

    lookup_field = 'public_id'
    lookup_url_kwarg = 'id'

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
        tasks.delete_resources(instance.public_id)


class VideoUploadViewSet(viewsets.ViewSet):
    """
    Generate video upload urls.
    """
    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = PERMISSION_CLASSES

    def create(self, request):
        filename = request.data.get('filename')
        if not filename:
            raise exceptions.ValidationError("Missing filename parameter")
        if len(filename) > 128:
            raise exceptions.ValidationError("Invalid filename parameter (> 128 characters)")
        url_info = tasks.create_upload_url(filename)
        return Response(url_info)

from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from pipeline.videoupload import get_upload_url
from video.models import Video
from . import serializers


AUTHENTICATION_CLASSES = (BasicAuthentication, SessionAuthentication, TokenAuthentication)
PERMISSION_CLASSES = (IsAuthenticated,)


class VideoViewSet(viewsets.ModelViewSet):
    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = PERMISSION_CLASSES

    queryset = Video.objects.all()
    serializer_class = serializers.VideoSerializer


class VideoUploadViewSet(viewsets.ViewSet):
    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = PERMISSION_CLASSES

    def create(self, request):
        url_info = get_upload_url()
        return Response(url_info)

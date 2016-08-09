from rest_framework import serializers

from pipeline import models


class VideoTranscodingSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ('status', 'progress', 'started_at')
        model = models.VideoTranscoding


class VideoSubtitlesSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='public_id', read_only=True)

    class Meta:
        fields = ('id', 'language')
        model = models.VideoSubtitles


class VideoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='public_id', read_only=True)
    status_details = VideoTranscodingSerializer(source='transcoding', read_only=True)
    subtitles = VideoSubtitlesSerializer(many=True, read_only=True)

    class Meta:
        fields = ('id', 'title', 'status_details', 'subtitles',)
        model = models.Video

from rest_framework import serializers

from pipeline import models


class PlaylistSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='public_id', read_only=True)
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        fields = ('id', 'name', 'owner')
        model = models.Playlist


class ProcessingStateSerializer(serializers.ModelSerializer):
    started_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ")

    class Meta:
        fields = ('status', 'progress', 'started_at')
        model = models.ProcessingState


class SubtitleSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='public_id', read_only=True)
    video_id = serializers.CharField(source='video__id', read_only=True)
    url = serializers.CharField(read_only=True)

    class Meta:
        fields = ('id', 'language', 'video_id', 'url')
        model = models.Subtitle


class VideoFormatSerializer(serializers.ModelSerializer):
    url = serializers.CharField(read_only=True)
    bitrate = serializers.FloatField(read_only=True)

    class Meta:
        fields = ('name', 'url', 'bitrate',)
        model = models.VideoFormat


class VideoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='public_id', read_only=True)
    processing = ProcessingStateSerializer(source='processing_state', read_only=True)
    subtitles = SubtitleSerializer(many=True, read_only=True)
    formats = VideoFormatSerializer(many=True, read_only=True)

    class Meta:
        fields = ('id', 'title', 'processing', 'subtitles', 'formats',)
        model = models.Video

from rest_framework import serializers

from pipeline import models


class PlaylistSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='public_id', read_only=True)
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        fields = ('id', 'name', 'owner')
        model = models.Playlist


class VideoTranscodingSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ('status', 'progress', 'started_at')
        model = models.VideoTranscoding


class VideoSubtitlesSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='public_id', read_only=True)
    video_id = serializers.CharField(source='video__id', read_only=True)
    download_url = serializers.CharField(read_only=True)

    class Meta:
        fields = ('id', 'language', 'video_id', 'download_url')
        model = models.VideoSubtitles


class VideoFormatSerializer(serializers.ModelSerializer):
    streaming_url = serializers.CharField(read_only=True)

    class Meta:
        fields = ('name', 'streaming_url')
        model = models.VideoFormat


class VideoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='public_id', read_only=True)
    status_details = VideoTranscodingSerializer(source='transcoding', read_only=True)
    subtitles = VideoSubtitlesSerializer(many=True, read_only=True)
    formats = VideoFormatSerializer(many=True, read_only=True)

    class Meta:
        fields = ('id', 'title', 'status_details', 'subtitles', 'formats',)
        model = models.Video

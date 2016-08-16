from django.contrib import admin

from . import models


class VideoTranscodingInlineAdmin(admin.TabularInline):
    model = models.VideoTranscoding


class VideoAdmin(admin.ModelAdmin):
    list_display = (
        'public_id', 'title', 'owner',
        'transcoding_progress', 'transcoding_status', 'transcoding_started_at',
    )
    inlines = [VideoTranscodingInlineAdmin]

    def get_queryset(self, request):
        qs = super(VideoAdmin, self).get_queryset(request)
        return qs.select_related('transcoding')


class VideoUploadUrlAdmin(admin.ModelAdmin):
    model = models.VideoUploadUrl
    list_display = ('public_video_id', 'owner', 'expires_at', 'was_used', 'last_checked',)


class PlaylistAdmin(admin.ModelAdmin):
    model = models.Playlist
    list_display = ('public_id', 'name', 'owner',)


admin.site.register(models.Video, VideoAdmin)
admin.site.register(models.VideoUploadUrl, VideoUploadUrlAdmin)
admin.site.register(models.Playlist, PlaylistAdmin)

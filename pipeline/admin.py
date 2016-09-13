from django.contrib import admin

from . import models


class ProcessingStateInlineAdmin(admin.TabularInline):
    model = models.ProcessingState


class VideoAdmin(admin.ModelAdmin):
    list_display = (
        'public_id', 'title', 'owner',
        'processing_progress', 'processing_status', 'processing_started_at',
    )
    inlines = [ProcessingStateInlineAdmin]

    def get_queryset(self, request):
        qs = super(VideoAdmin, self).get_queryset(request)
        return qs.select_related('processing_state')


class VideoUploadUrlAdmin(admin.ModelAdmin):
    model = models.VideoUploadUrl
    list_display = ('public_video_id', 'owner', 'expires_at', 'was_used',)


class PlaylistAdmin(admin.ModelAdmin):
    model = models.Playlist
    list_display = ('public_id', 'name', 'owner',)


admin.site.register(models.Video, VideoAdmin)
admin.site.register(models.VideoUploadUrl, VideoUploadUrlAdmin)
admin.site.register(models.Playlist, PlaylistAdmin)

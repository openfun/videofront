from django.contrib import admin

from . import models


class ProcessingStateInlineAdmin(admin.TabularInline):
    model = models.ProcessingState


class VideoAdmin(admin.ModelAdmin):
    list_display = (
        'public_id', 'title', 'owner',
        'processing_progress', 'processing_status', 'processing_started_at',
    )
    search_fields = ('title', 'public_id',)
    list_filter = ('owner',)
    raw_id_fields = ('owner',)
    inlines = [ProcessingStateInlineAdmin]

    def get_queryset(self, request):
        qs = super(VideoAdmin, self).get_queryset(request)
        return qs.select_related('processing_state')


class VideoUploadUrlAdmin(admin.ModelAdmin):
    model = models.VideoUploadUrl
    list_display = ('public_video_id', 'owner', 'expires_at', 'was_used',)
    list_filter = ('owner',)
    raw_id_fields = ('owner',)
    search_fields = ('public_video_id',)


class PlaylistAdmin(admin.ModelAdmin):
    model = models.Playlist
    list_display = ('public_id', 'name', 'owner',)
    list_filter = ('owner',)
    raw_id_fields = ('owner',)
    search_fields = (
        'public_id', 'name', 'videos__public_id',
        'videos__title'
    )
    filter_horizontal = ('videos',)


class SubtitleAdmin(admin.ModelAdmin):
    model = models.Subtitle
    list_display = ('public_id', 'video', 'language')
    list_filter = ('language',)
    raw_id_fields = ('video',)
    search_fields = ('public_id', 'video__public_id', 'video__title')


class VideoFormatAdmin(admin.ModelAdmin):
    model = models.VideoFormat
    list_display = ('__str__', 'name', 'video', 'bitrate')
    raw_id_fields = ('video',)
    search_fields = ('name', 'bitrate', 'video_public_id', 'video__title')


admin.site.register(models.Video, VideoAdmin)
admin.site.register(models.VideoUploadUrl, VideoUploadUrlAdmin)
admin.site.register(models.Playlist, PlaylistAdmin)
admin.site.register(models.Subtitle, SubtitleAdmin)
admin.site.register(models.VideoFormat, VideoFormatAdmin)

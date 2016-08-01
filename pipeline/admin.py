from django.contrib import admin

from . import models

class VideoTranscodingInlineAdmin(admin.TabularInline):
    model = models.VideoTranscoding

class VideoAdmin(admin.ModelAdmin):
    list_display = ('public_id', 'title', 'transcoding_progress', 'transcoding_status', 'transcoding_started_at')
    inlines = [VideoTranscodingInlineAdmin]

    def get_queryset(self, request):
        qs = super(VideoAdmin, self).get_queryset(request)
        return qs.select_related('transcoding')

class VideoUploadUrlAdmin(admin.ModelAdmin):
    model = models.VideoUploadUrl
    list_display = ('public_video_id', 'expires_at', 'was_used', 'last_checked')

admin.site.register(models.Video, VideoAdmin)
admin.site.register(models.VideoUploadUrl, VideoUploadUrlAdmin)

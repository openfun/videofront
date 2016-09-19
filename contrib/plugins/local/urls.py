from django.conf.urls import url

from . import views

urlpatterns = [
    # Note that this url should be served by the webserver (ex: nginx) for efficiency reasons.
    url(r'^storage/videos/(?P<video_id>.+)/(?P<format_name>.+)\.mp4$', views.storage_video, name='storage-video'),
]

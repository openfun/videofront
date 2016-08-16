from django.conf.urls import url, include

from rest_framework.authtoken import views as authtoken_views
from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register(r'playlists', views.PlaylistViewSet, base_name='playlist')
router.register(r'videos', views.VideoViewSet, base_name='video')
router.register(r'videouploads', views.VideoUploadViewSet, base_name='videoupload')

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^auth-token/', authtoken_views.obtain_auth_token, name='auth-token')
]

from django.conf.urls import url, include

from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register(r'videos', views.VideoViewSet)
router.register(r'videouploads', views.VideoUploadViewSet, base_name='videoupload')

urlpatterns = [
    url(r'^', include(router.urls)),
]

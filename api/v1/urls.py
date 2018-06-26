"""Url definitions for version 1 of the Video Front API"""
from django.conf.urls import include, url

from rest_framework import routers
from rest_framework.authtoken import views as authtoken_views

from . import views


class Router(routers.DefaultRouter):
    """
    We override the router in order to provide some documentation to the API root.
    """

    def get_api_root_view(self, api_urls=None):
        """
        Populate the __doc__ attribute of the root view before returning it
        """
        root_view = super().get_api_root_view(api_urls=api_urls)
        root_view.cls.__doc__ = """List of all the endpoints from the videofront API.

        A more detailed and interactive documentation may be found [here](/api/v1/docs).
        """
        return root_view


router = Router()
router.register(r"playlists", views.PlaylistViewSet, base_name="playlist")
router.register(r"subtitles", views.SubtitleViewSet, base_name="subtitle")
router.register(r"users", views.UserViewSet)
router.register(r"videos", views.VideoListViewSet, base_name="video")
router.register(r"videos", views.VideoViewSet, base_name="video")
router.register(r"videos", views.UploadViewset, base_name="video")
router.register(
    r"videouploadurls", views.VideoUploadUrlViewSet, base_name="videouploadurl"
)

urlpatterns = [
    url(r"^", include(router.urls)),
    url(r"^docs$", views.schema_view),
    url(r"^auth-token/", authtoken_views.obtain_auth_token, name="auth-token"),
]

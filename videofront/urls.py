from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import RedirectView


urlpatterns = [
    url(r"^$", RedirectView.as_view(pattern_name="api:v1:api-root"), name="home"),
    url(r"^api/", include("api.urls")),
    url(r"^admin/", admin.site.urls),
]

"""
Url definitions for the Video Front API.
Just including routes for all versions of the API
"""
from django.conf.urls import include, url

urlpatterns = [url(r"^v1/", include("api.v1.urls", namespace="v1"))]

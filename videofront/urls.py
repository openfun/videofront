"""
URLs for videofront
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import RedirectView
import django_app_lti.urls
from django.contrib.auth import views as auth_views

urlpatterns = [
    url(r"^$", RedirectView.as_view(pattern_name="api:v1:api-root"), name="index"),
    url(r"^api/", include("api.urls", namespace="api")),
    url(r"^admin/", admin.site.urls),
    url(r'^lti/', include(django_app_lti.urls, namespace="lti")),
    url(r'^login/$', auth_views.login, {'template_name': 'registration/login.html'}, name='login'),
    url(r'^logout/$', auth_views.logout, {'template_name': 'logged_out.html'},name='logout'),
    url(r'^ltivideofront/', include('ltivideofront.urls',namespace="ltivideofront")),

]

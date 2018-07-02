from django.conf.urls import url
from .views import LTILaunchView, LTIToolConfigView, logout_view, logged_out_view

urlpatterns = [
    url(r'^$', LTILaunchView.as_view(), name='index'),
    url(r'^launch$', LTILaunchView.as_view(), name='launch'),
    url(r'^config$', LTIToolConfigView.as_view(), name='config'),
    url(r'^logout$', logout_view, name="logout"),
    url(r'^logged-out$', logged_out_view, name="logged-out"),
]

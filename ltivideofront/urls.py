"""
URLs for ltivideofront
"""
from django.conf.urls import include, url
from . import views
from .views import MyLTILaunchView
app_name='ltivideofront'

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^launch$', MyLTILaunchView.as_view(), name='launch'),

]

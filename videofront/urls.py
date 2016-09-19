from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic import RedirectView

urlpatterns = [
    url(r'^$', RedirectView.as_view(pattern_name='api:v1:api-root'), name='home'),

    url(r'^api/', include('api.urls', namespace="api")),

    url(r'^admin/', admin.site.urls),
]

if hasattr(settings, 'BACKEND_URLS'):
    # Include backend-specific urls
    urlpatterns.append(url(r'^backend/', include(settings.BACKEND_URLS)))

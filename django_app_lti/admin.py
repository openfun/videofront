from django.contrib import admin
from django_app_lti.models import LTICourse, LTICourseUser, LTIResource

admin.site.register(LTICourse)
admin.site.register(LTICourseUser)
admin.site.register(LTIResource)

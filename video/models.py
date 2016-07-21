from __future__ import unicode_literals

from django.db import models


class Video(models.Model):
    title = models.CharField(max_length=100)

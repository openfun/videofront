# Add models here
from __future__ import unicode_literals

from django.db import models
import uuid

def generate_strong_secret():
    return uuid.uuid4().hex

class LTIOauthCredentials(models.Model):
    key = models.CharField(max_length=255, unique=True)
    secret = models.CharField(max_length=255, unique=True, default=generate_strong_secret)
    enabled = models.BooleanField(default=True)

    org_name = models.CharField(max_length=255)
    org_contact_email = models.EmailField()
    org_contact_firstname = models.CharField(max_length=255)
    org_contact_lastname = models.CharField(max_length=255)

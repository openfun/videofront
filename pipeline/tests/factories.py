"""
Use factory boy to create random instances of each model in the application for testing purpose
"""
from django.contrib.auth.models import User

import factory.django

from pipeline import models


class UserFactory(factory.django.DjangoModelFactory):
    """
    This fatory creates random user instances for testing purposes
    """

    class Meta:
        model = User

    username = factory.Sequence(lambda n: "User %d" % n)


class VideoUploadUrlFactory(factory.DjangoModelFactory):
    """
    This fatory creates random video upload URL instances for testing purposes
    """

    class Meta:
        model = models.VideoUploadUrl

    owner = factory.SubFactory(UserFactory)


class VideoFactory(factory.DjangoModelFactory):
    """
    This fatory creates random video instances for testing purposes
    """

    class Meta:
        model = models.Video

    owner = factory.SubFactory(UserFactory)


class PlaylistFactory(factory.DjangoModelFactory):
    """
    This fatory creates random playlist instances for testing purposes
    """

    class Meta:
        model = models.Playlist

    owner = factory.SubFactory(UserFactory)


class SubtitleFactory(factory.DjangoModelFactory):
    """
    This fatory creates random subtitle instances for testing purposes
    """

    class Meta:
        model = models.Subtitle

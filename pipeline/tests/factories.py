from django.contrib.auth.models import User

import factory.django

from pipeline import models


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: "User %d" % n)


class VideoUploadUrlFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.VideoUploadUrl

    owner = factory.SubFactory(UserFactory)


class VideoFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Video

    owner = factory.SubFactory(UserFactory)


class PlaylistFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Playlist

    owner = factory.SubFactory(UserFactory)


class SubtitleFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Subtitle

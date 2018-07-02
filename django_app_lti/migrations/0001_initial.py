# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LTICourse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('course_name_short', models.CharField(max_length=1024)),
                ('course_name', models.CharField(max_length=2048)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['course_name_short', 'course_name'],
                'verbose_name': 'LTI Course',
                'verbose_name_plural': 'LTI Courses ',
            },
        ),
        migrations.CreateModel(
            name='LTICourseUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('roles', models.CharField(max_length=2048, null=True, verbose_name=b'Roles', blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(to='django_app_lti.LTICourse')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['course', 'user', 'roles'],
                'verbose_name': 'LTI Course Users',
                'verbose_name_plural': 'LTI Course Users ',
            },
        ),
        migrations.CreateModel(
            name='LTIResource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('consumer_key', models.CharField(max_length=255)),
                ('resource_link_id', models.CharField(max_length=255)),
                ('context_id', models.CharField(max_length=255, null=True, blank=True)),
                ('canvas_course_id', models.CharField(max_length=255, null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(to='django_app_lti.LTICourse', null=True)),
            ],
            options={
                'ordering': ['consumer_key', 'resource_link_id', 'context_id'],
                'verbose_name': 'LTI Resource',
                'verbose_name_plural': 'LTI Resources',
            },
        ),
    ]

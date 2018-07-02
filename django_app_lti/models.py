from django.db import models
from django.conf import settings
from pipeline.models import Playlist

class LTICourse(models.Model):
    course_name_short = models.CharField(max_length=1024)
    course_name = models.CharField(max_length=2048)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    @classmethod
    def getCourseNames(cls, course_id):
        result = {"name": "", "name_short": ""}
        if cls.objects.filter(id=course_id).exists():
            c = cls.objects.get(id=course_id)
            result['name'] = c.course_name
            result['name_short'] = c.course_name_short
        return result
    
    def __unicode__(self):
        return "%s (ID: %s)" % (self.course_name, self.id)

    class Meta:
        verbose_name = 'LTI Course'
        verbose_name_plural = 'LTI Courses '
        ordering = ['course_name_short','course_name']

class LTICourseUser(models.Model):
    course = models.ForeignKey(LTICourse)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    roles = models.CharField(max_length=2048, blank=True, null=True, verbose_name="Roles")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    @classmethod
    def hasCourseUser(cls, user, course):
        return cls.objects.filter(user=user, course=course).exists()
 
    @classmethod
    def getCourseUser(cls, user, course):
        result = cls.objects.filter(user=user, course=course)
        if len(result) > 0:
            return result[0]
        return None
   
    @classmethod
    def createCourseUser(cls, user, course, roles=''):
        course_user = cls.objects.create(user=user, course=course, roles=roles)
        return course_user
    
    def updateRoles(self, roles):
        if self.roles != roles:
            self.roles = roles
            self.save()
            return True
        return False

    def __unicode__(self):
        return "%s %s (Roles: %s)" % (self.course.course_name_short, self.user.username, self.roles)

    class Meta:
        verbose_name = 'LTI Course Users'
        verbose_name_plural = 'LTI Course Users '
        ordering = ['course','user', 'roles']

class LTIResource(models.Model):
    consumer_key = models.CharField(max_length=255, blank=False)
    resource_link_id = models.CharField(max_length=255, blank=False)
    context_id = models.CharField(max_length=255, blank=True, null=True)
    canvas_course_id = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    course = models.ForeignKey(LTICourse, null=True)
    playlists= models.ManyToManyField(Playlist)

    @classmethod
    def hasResource(cls, consumer_key, resource_link_id):
        return cls.objects.filter(consumer_key=consumer_key,resource_link_id=resource_link_id).exists()
    
    @classmethod
    def getResource(cls, consumer_key, resource_link_id):
        result = cls.objects.filter(consumer_key=consumer_key,resource_link_id=resource_link_id)
        if len(result) > 0:
            return result[0]
        return None
    
    @classmethod
    def setupResource(cls, launch, create_course=False):
        if not ("consumer_key" in launch and "resource_link_id" in launch): 
            raise Exception("Missing required launch parameters: consumer_key and resource_link_id")
        
        course = None
        course_name_short = launch.pop('course_name_short', 'untitled')
        course_name = launch.pop('course_name', 'Untitled Course')
        if create_course:
            course = LTICourse.objects.create(course_name_short=course_name_short,course_name=course_name)
 
        return cls.objects.create(course=course, **launch)

    def __unicode__(self):
        return "%s %s (Canvas Course ID: %s)" % (self.consumer_key, self.resource_link_id, self.canvas_course_id)

    class Meta:
        verbose_name = 'LTI Resource'
        verbose_name_plural = 'LTI Resources'
        ordering = ['consumer_key','resource_link_id', 'context_id']

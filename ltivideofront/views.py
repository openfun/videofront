from django.http import HttpResponsePermanentRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import render,redirect,render_to_response
import json
from django_app_lti.views import LTILaunchView
from django.contrib.auth.models import User
import logging
from django.template import RequestContext
from django_app_lti.models import LTIResource
app_name = 'LTIFRONT'
logger = logging.getLogger(__name__)

def index(request):
    id_xblock=request.session["id_xblock"]
    logger.info("////////id_xblock%s" % id_xblock)
    resourcelink=LTIResource.objects.filter(resource_link_id=id_xblock)
    if resourcelink.exists():
         logger.info("////////existe")
         for playlist in resourcelink[0].playlists:
                logger.info("////////playlistname" )
    return render(request,'home.html', {})

class MyLTILaunchView(LTILaunchView):
    def hook_before_post(self, request):
        '''Called before models are created and initialized in hook_process_post().'''

        pass

    def hook_process_post(self, request):
        '''Creates and initializes models.'''
        super(MyLTILaunchView, self).hook_process_post(request)

    def hook_after_post(self, request):
        '''Called after models are initialized.'''
        pass

    def hook_get_redirect(self):
        return super(MyLTILaunchView, self).hook_get_redirect()


DEBUG = True
SECRET_KEY = "secret"
TEMPLATE_DEBUG = True
ALLOWED_HOSTS = []
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.staticfiles',
    'django.contrib.contenttypes',
    'django_app_lti',
)
MIDDLEWARE_CLASSES = ()
ROOT_URLCONF = 'django_app_lti.urls'
DATABASES = {
    'default': { 
        'ENGINE': 'django.db.backends.sqlite3', 
        'NAME': 'mydatabase'
    }
}
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LTI_SETUP = {
    "TOOL_TITLE": "Test Tool Title",
    "TOOL_DESCRIPTION": "Test Tool Description",
    "LAUNCH_REDIRECT_URL": "index",
    "LAUNCH_URL": "launch",
}

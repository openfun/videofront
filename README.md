# Videofront

A scalable video hosting platform written in Django.

Initially, Videofront was developed to host videos of MOOCs taught on [Open edX](https://open.edx.org/) platforms, but it can easily be used in just any web platform that requires video embedding.

## Features

- Video storage, transcoding and streaming
- A RESTful API, with a browsable GUI powered by [Swagger](http://swagger.io/)
- A flexible and extensible set of backends to store and process videos from different providers. Out of the box, Amazon Web Services (S3 + ElasticTranscoder + Cloudfront) support is provided.
- A basic user permission system for interacting with the API
- Command line and browser-based video upload (with [CORS](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing))
- Subtitle upload, conversion to [VTT](https://w3c.github.io/webvtt/) format, storage and download
- Thumbnail generation and customisation

## TODO

Videofront is still in early beta, although it is already used in production at [FUN-MOOC](https://fun-mooc.fr). Here is the list of upcoming features, by decreasing priority:

- Development of a backend for local storage, transcoding and streaming
- Creation of an `/embed` endpoint for easy video integration inside iframes
- Viewer statistics
- More evolved permission system, with public & private videos
- ... We are open to feature requests!

## Install

Clone the repository:

    git clone https://github.com/openfun/videofront.git
    cd videofront/

Install non-python requirements:

    sudo apt-get install rabbitmq-server libxml2-dev libxslt1-dev libtiff5-dev libjpeg8-dev zlib1g-dev

Install python requirements in a virtual environment:

    virtualenv --python=python3 venv # note that python3 is required
    source venv/bin/activate
    pip install -r requirements/base.txt

If you wish to interact with Amazon Web Services, additional dependencies need to be installed:

    pip install -r requirements/aws.txt

Note that you will also need to install and configure an SQL database.

Create database tables:

    ./manage.py migrate
    ./manage.py createcachetable

## Usage

You will first need to create a user in Videofront to obtain a token and start interacting with the API:

    $ ./manage.py createuser chucknorris fantasticpassword
    Created user 'chucknorris' with token: 6f6801edef3f4b74378f2ac270be464b351efefe

Start a local server:

    $ ./manage.py runserver

Start a celery worker for periodic and non-periodic tasks:

    celery -A videofront worker -B # don't do this in production

Obtain a video upload url:

    $ curl -X POST -H "Authorization: Token 6f6801edef3f4b74378f2ac270be464b351efefe" http://127.0.0.1:8000/api/v1/videouploadurls/
    {"id":"0sqmLiEuLpGJ","expires_at":1474362128,"origin":null,"playlist":null}(env3)

Upload a video to this url:

    $ curl -X POST -H "Authorization: Token 6f6801edef3f4b74378f2ac270be464b351efefe" -F file=@video.mp4 http://127.0.0.1:8000/api/v1/videos/0sqmLiEuLpGJ/upload/

Alternatively, you may use the [videofront-client](https://github.com/openfun/videofront-client) package instead of `curl` for easier interaction with the API.

## Development

Install test and contrib requirements:

    pip install -r requirements/tests.txt
    pip install -r requirements/aws.txt

Run unit tests:

    ./manage.py test

Check test coverage:

    coverage run ./manage.py test
    coverage report

## Deployment

### Production settings

Pick a backend and customize the settings file accordingly:

    cp videofront/settings_prod_sample_aws.py videofront/settings_prod.py
    # edit videofront/settings_prod.py

### Start gunicorn and celery workers

The recommended approach is to start gunicorn and celery workers with `supervisorctl`:

    $ cat /etc/supervisor/conf.d/videofront.conf 
    [group:videofront]
    programs=gunicorn,celery,celery-beat

    [program:gunicorn]
    command=/home/user/videofront/venv/bin/gunicorn --name videofront --workers 12 --bind=127.0.0.1:8000 --log-level=INFO videofront.wsgi:application
    directory=/home/user/videofront/src/videofront/
    environment=DJANGO_SETTINGS_MODULE="videofront.settings_prod"
    autostart=true
    autorestart=true
    user=videofront
    priority=997

    [program:celery]
    directory=/home/user/videofront/src/videofront/
    command=/home/user/videofront/venv/bin/celery worker -A videofront --loglevel=INFO --pidfile=/home/user/videofront/celery/w1.pid --hostname 'w1.%%h'
    environment=DJANGO_SETTINGS_MODULE="videofront.settings_prod"
    autostart=true
    autorestart=true
    user=videofront
    priority=998

    [program:celery-beat]
    directory=/home/user/videofront/src/videofront/
    command=/home/user/videofront/venv/bin/celery beat -A videofront --loglevel=INFO --pidfile=/home/user/videofront/celery/beat.pid --schedule /opt/videofront/celery/celerybeat-schedule
    environment=DJANGO_SETTINGS_MODULE="videofront.settings_prod"
    autostart=true
    autorestart=true
    user=videofront
    priority=999

### Serve content with nginx

Recommended nginx configuration:

    $ cat /etc/nginx/sites-enabled/videofront.vhost 
    upstream django {
        server 127.0.0.1:8001;
    }

    server {
        listen 80;
        server_name example.com;

        client_max_body_size 20M;

        location /static/ {
          # This depends on the STATIC_ROOT setting
          alias /home/user/videofront/static/;
        }
        
        location / {
            location ~ ^/api/v1/videos/(?P<video_id>.*)/upload/ {
                # Max video upload size
                client_max_body_size 1G;
            }

            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $http_host;
            proxy_redirect off;
            proxy_pass django;
        }
    }

## Custom commands

    # Create a user and print out the corresponding access token
    ./manage.py createuser --admin username password

    # Launch a new video transcoding job; useful if the transcoding job is stuck in pending state
    ./manage.py transcode-video myvideoid

AWS-specific commands:

    # Create S3 buckets according to your settings
    ./manage.py bootstrap-s3

    # Delete folders from the production S3 bucket
    ./manage.py delete-s3-folders videos/xxx folder1/ folder2/somefile.mp4

## License

The code in this repository is licensed under version 3 of the AGPL unless otherwise noted. Your rights and duties are summarised [here](https://tldrlegal.com/license/gnu-affero-general-public-license-v3-(agpl-3.0)). Please see the LICENSE file for details.

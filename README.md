# Videofront

A video upload, transcoding, storage and streaming backend written in Django.

## Install

Clone the repository:

    git clone https://github.com/openfun/videofront.git
    cd videofront/

Install non-python requirements:

    sudo apt-get install rabbitmq-server

Install python requirements in a virtual environment:

    virtualenv venv && source venv/bin/activate
    pip install -r requirements/base.txt

If you wish to interact with Amazon Web Services, additional dependencies need to be installed:

    pip install -r requirements/aws.txt

Create database tables:

    ./manage.py migrate
    ./manage.py createcachetable

Run a development server on port 9000:

    ./manage.py runserver 9000

## Usage

It's a good idea to create a user; the following command will automatically generate an authentication token, useful for later calls to the API:

    ./manage.py createuser chucknorris fantasticpassword

You can then try to upload a video to test your infrastructure:

    ./scripts/uploadvideo --token chucknorrishasatoken /path/to/myvideo.mp4

Note that you will need a running videofront server and celery workers to make this command work.

## Development

Install test and contrib requirements:

    pip install -r requirements/tests.txt
    pip install -r requirements/aws.txt

Run unit tests:

    ./manage.py test

Check test coverage:

    coverage run ./manage.py tet
    coverage report

## Deployment

Test production settings locally:

    DJANGO_SETTINGS_MODULE=videofront.settings_prod ./manage.py runserver

Run celery workers:

    export DJANGO_SETTINGS_MODULE=videofront.settings_prod 
    celery -A videofront worker
    celery -A videofront beat # periodic tasks

Depending on your infrastructure, you will need to use different settings in production. In videofront, the same task can be performed by different plugins. You will have to choose the right implementation for each plugin. For instance, if you wish to store files on Amazon S3, then upload urls will have to be generated for S3 and the following plugin will have to be overridden in the production settings:

    # videofron/settings_prod_sample.py
    ...
    PLUGINS["GET_UPLOAD_URL"] = "contrib.plugins.aws.video.get_upload_url"
    ...

Note that if you need to access AWS services, the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` setting variables will have to be defined.

## License

The code in this repository is licensed under version 3 of the AGPL unless otherwise noted. Your rights and duties are summarised [here](https://tldrlegal.com/license/gnu-affero-general-public-license-v3-(agpl-3.0)). Please see the LICENSE file for details.

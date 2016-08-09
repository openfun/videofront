# Videofront

A video upload, transcoding, storage and streaming backend written in Django.

## Install

Clone the repository:

    git clone https://github.com/openfun/videofront.git
    cd videofront/

Install non-python requirements:

    sudo apt-get install rabbitmq-server

Install python requirements in a virtual environment:

    virtualenv --python=python3 venv # note that python3 is required
    source venv/bin/activate
    pip install -r requirements/base.txt

If you wish to interact with Amazon Web Services, additional dependencies need to be installed:

    pip install -r requirements/aws.txt

Create database tables:

    ./manage.py migrate
    ./manage.py createcachetable

## Usage

It's a good idea to create a user; the following command will automatically generate an authentication token, useful for later calls to the API:

    ./manage.py createuser chucknorris fantasticpassword

Using the [videofront-client](https://github.com/openfun/videofront-client) package, you can then try to upload a video to test your infrastructure.

## Development

Install test and contrib requirements:

    pip install -r requirements/tests.txt
    pip install -r requirements/aws.txt

Run unit tests:

    ./manage.py test

Check test coverage:

    coverage run ./manage.py tet
    coverage report

Run a development server on port 9000:

    ./manage.py runserver 9000

Start a celery worker for periodic and non-periodic tasks:

    celery -A videofront worker -B # don't do this in production

## Deployment

Depending on your infrastructure, you will need to use different settings in production. In videofront, the same task can be performed by different plugins. You will have to choose the right implementation for each plugin. For instance, if you wish to store files on Amazon S3, then upload urls will have to be generated for S3 and the following plugin will have to be overridden in the production settings:

    # videofron/settings_prod_sample.py
    ...
    PLUGINS["GET_UPLOAD_URL"] = "contrib.plugins.aws.video.get_upload_url"
    ...

Note that if you need to access AWS services, you will have to define various AWS-specific setting variables described in settings_prod_sample.py

Test production settings locally:

    export DJANGO_SETTINGS_MODULE=videofront.settings_prod 
    ./manage.py runserver

Run celery workers:

    celery -A videofront worker
    celery -A videofront beat # periodic tasks

## License

The code in this repository is licensed under version 3 of the AGPL unless otherwise noted. Your rights and duties are summarised [here](https://tldrlegal.com/license/gnu-affero-general-public-license-v3-(agpl-3.0)). Please see the LICENSE file for details.

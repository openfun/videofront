BOLD := \033[1m
RESET := \033[0m

# If you want to use a virtualenv on your machine instead of Docker, set the NO_DOCKER variable to
# something not null. All commands will then be run on your machine instead of being run in the
# Docker container using "docker-compose".
ifndef NO_DOCKER
	# Docker
	COMPOSE              = docker-compose
	COMPOSE_RUN          = $(COMPOSE) run --rm
	COMPOSE_RUN_APP      = $(COMPOSE_RUN) app
	COMPOSE_TEST         = $(COMPOSE) -p videofront-test -f docker/compose/test/docker-compose.yml --project-directory .
	COMPOSE_TEST_RUN     = $(COMPOSE_TEST) run --rm
	COMPOSE_TEST_RUN_APP = $(COMPOSE_TEST_RUN) app
endif

default: help

.PHONY : help
help:  ## Show this help
	@echo "$(BOLD)VideoFront Makefile$(RESET)"
	@echo "Please use 'make $(BOLD)target$(RESET)' where $(BOLD)target$(RESET) is one of:"
	@grep -h ':\s\+##' Makefile | column -tn -s# | awk -F ":" '{ print "  $(BOLD)" $$1 "$(RESET)" $$2 }'

##########################################################
# Targets that work for Docker or Virtualenv installations
#  (you must set the NO_DOCKER environment variable to install without Docker)

lint: ## lint back-end python sources
	${MAKE} lint-isort;
	${MAKE} lint-black;  # black should come after isort just in case they don't agree...
	${MAKE} lint-flake8;
	${MAKE} lint-pylint;
.PHONY: lint

lint-black: ## lint back-end python sources with black
	@echo 'lint:black started…';
	@$(COMPOSE_TEST_RUN_APP) black api contrib pipeline transcoding videofront;
.PHONY: lint-black

lint-flake8: ## lint back-end python sources with flake8
	@echo 'lint:flake8 started…';
	@$(COMPOSE_TEST_RUN_APP) flake8;
.PHONY: lint-flake8

lint-isort: ## automatically re-arrange python imports in back-end code base
	@echo 'lint:isort started…';
	@$(COMPOSE_TEST_RUN_APP) isort --recursive --atomic .;
.PHONY: lint-isort

lint-pylint: ## lint back-end python sources with pylint
	@echo 'lint:pylint started…';
	@$(COMPOSE_TEST_RUN_APP) pylint api contrib pipeline transcoding videofront;
.PHONY: lint-pylint

test: ## run back-end tests
	@$(COMPOSE_TEST_RUN_APP) pytest
.PHONY: test

.PHONY: migrate
migrate:  ## Run django migration for the videofront project.
	@echo "$(BOLD)Running migrations$(RESET)"
	@$(COMPOSE_RUN_APP) python manage.py migrate

superuser: ## create a Django superuser
	@$(COMPOSE_RUN_APP) python manage.py createsuperuser
.PHONY: superuser

.PHONY: dist
dist:  ## Build the package
	@python setup.py sdist bdist_wheel

.PHONY: clean
clean:  ## Clean python build related directories and files
	@echo "$(BOLD)Cleaning$(RESET)"
	@rm -rf build dist videofront.egg-info

##############################################
# Targets specific to Virtualenv installations

.PHONY: install
install:  ## Install the project in the current environment, with its dependencies
	@pip install .[aws]

.PHONY: dev
dev:  ## Install the project in the current environment, with its dependencies, including the ones needed in a development environment
	@pip install -e .[aws,dev,quality,test]

##########################################
# Targets specific to Docker installations

.PHONY: bootstrap
bootstrap:  ## Prepare Docker images for the project
	@$(COMPOSE) build base;
	@$(COMPOSE) build app;
	@echo 'Waiting until database is up…';
	$(COMPOSE_RUN_APP) dockerize -wait tcp://db:5432 -timeout 60s
	${MAKE} migrate;

.PHONY: run
run: ## start the Docker development server
	@$(COMPOSE) up -d

stop: ## stop the Docker development server
	@$(COMPOSE) stop
.PHONY: stop

logs: ## get the Docker logs
	@$(COMPOSE) logs -f
.PHONY: logs

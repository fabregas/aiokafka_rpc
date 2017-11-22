SCALA_VERSION?=2.11
KAFKA_VERSION?=0.10.2.1
DOCKER_IMAGE=aiolibs/kafka:$(SCALA_VERSION)_$(KAFKA_VERSION)

setup:
	pip install -r requirements-dev.txt
	pip install -Ue .

flake:
	flake8 aiokafka_rpc tests 

test: flake
	pytest -s --no-print-logs --docker-image $(DOCKER_IMAGE) $(FLAGS) tests

vtest: flake
	pytest -s -vvv --no-print-logs --docker-image $(DOCKER_IMAGE) $(FLAGS) tests

cov cover coverage: flake
	pytest -s --no-print-logs --cov aiokafka_rpc --cov-report html --docker-image $(DOCKER_IMAGE) $(FLAGS) tests
	@echo "open file://`pwd`/htmlcov/index.html"

clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -f `find . -type f -name '@*' `
	rm -f `find . -type f -name '#*#' `
	rm -f `find . -type f -name '*.orig' `
	rm -f `find . -type f -name '*.rej' `
	rm -f .coverage
	rm -rf *.egg-info
	rm -rf htmlcov
	rm -rf docs/_build/
	rm -rf cover
	rm -rf build
	rm -rf dist

# Makefile
.PHONY: help install test run clean docker-build docker-run deploy lint format

help:
	@echo "Available commands:"
	@echo "  install     Install dependencies"
	@echo "  test        Run tests"
	@echo "  run         Run the application locally"
	@echo "  clean       Clean up temporary files"
	@echo "  docker-build Build Docker image"
	@echo "  docker-run  Run with Docker Compose"
	@echo "  deploy      Deploy to AWS"
	@echo "  lint        Run code linting"
	@echo "  format      Format code"

install:
	pip install -r requirements.txt
	pip install -e .

test:
	pytest tests/ -v --cov=app --cov-report=html

run:
	python main.py

clean:
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .pytest_cache/

docker-build:
	docker build -t mortgage-ml-app .

docker-run:
	docker-compose up --build

deploy:
	@echo "Deploying to AWS..."
	aws cloudformation deploy \
		--template-file infrastructure/cloudformation/ml-monitoring-stack.yaml \
		--stack-name mortgage-ml-monitoring \
		--capabilities CAPABILITY_IAM \
		--parameter-overrides \
			EnvironmentName=production \
			AlertEmail=${ALERT_EMAIL}

lint:
	flake8 app/ main.py
	mypy app/ main.py

format:
	black app/ main.py
	isort app/ main.py

# Local development setup
dev-setup: install
	@echo "Setting up local development environment..."
	docker-compose up -d localstack redis
	@echo "Waiting for LocalStack to be ready..."
	sleep 10
	@echo "Creating local AWS resources..."
	aws --endpoint-url=http://localhost:4566 s3 mb s3://mortgage-ml-models
	aws --endpoint-url=http://localhost:4566 dynamodb create-table \
		--table-name ModelRegistry \
		--attribute-definitions AttributeName=model_type,AttributeType=S AttributeName=version,AttributeType=S \
		--key-schema AttributeName=model_type,KeyType=HASH AttributeName=version,KeyType=RANGE \
		--billing-mode PAY_PER_REQUEST
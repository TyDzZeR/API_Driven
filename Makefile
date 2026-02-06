PYTHON = ./rep_localstack/bin/python
PIP = ./rep_localstack/bin/pip
LOCALSTACK = ./rep_localstack/bin/localstack

# Construct the external URL dynamically if running in Codespaces
# If not in Codespaces, it might fallback or need manual override, but we default to this structure for now.
EXTERNAL_URL ?= https://${CODESPACE_NAME}-4566.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}

.PHONY: all install start deploy clean

all: install start deploy

install:
	@echo "Creation de l'environnement virtuel..."
	test -d rep_localstack || python3 -m venv rep_localstack
	@echo "Installation des dependances..."
	$(PIP) install --upgrade pip
	$(PIP) install boto3 localstack

start:
	@echo "Demarrage de LocalStack..."
	$(LOCALSTACK) start -d
	@echo "Verification des services..."
	$(LOCALSTACK) status services

deploy:
	@echo "Deploying infrastructure..."
	@echo "External endpoint detected: $(EXTERNAL_URL)"
	@AWS_ACCESS_KEY_ID=test \
	AWS_SECRET_ACCESS_KEY=test \
	AWS_REGION=us-east-1 \
	AWS_ENDPOINT_URL=$(EXTERNAL_URL) \
	$(PYTHON) infrastructure/deploy.py

clean:
	rm -f function.zip

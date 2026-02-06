PYTHON = ./rep_localstack/bin/python
PIP = ./rep_localstack/bin/pip

# Construct the external URL dynamically if running in Codespaces
# If not in Codespaces, it might fallback or need manual override, but we default to this structure for now.
EXTERNAL_URL ?= https://${CODESPACE_NAME}-4566.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}

.PHONY: all install deploy clean

all: install deploy

install:
	@echo "Installing dependencies..."
	$(PIP) install boto3

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

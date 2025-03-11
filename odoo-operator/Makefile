# Image URL to use all building/pushing image targets
IMG ?= bemade/odoo-operator:latest

# Setting SHELL to bash allows bash commands to be executed by recipes
SHELL = /usr/bin/env bash

.PHONY: all
all: docker-build

##@ General

# The help target prints out all targets with their descriptions organized
# beneath their categories. The categories are represented by '##@' and the
# target descriptions by '##'. The awk commands is responsible for reading the
# entire set of makefiles included in this invocation, looking for lines of the
# file as xyz: ## something, and then pretty-format the target and help. Then,
# if there's a line with ##@ something, that gets pretty-printed as a category.
.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

.PHONY: lint
lint: ## Run linting on Python code.
	pylint python/*.py

.PHONY: test
test: ## Run tests.
	python -m pytest python/tests

.PHONY: run
run: ## Run the operator locally.
	kopf run python/operator.py --verbose

##@ Build

.PHONY: docker-build
docker-build: ## Build docker image with the operator.
	docker build -t ${IMG} .

.PHONY: docker-push
docker-push: ## Push docker image with the operator.
	docker push ${IMG}

##@ Deployment

.PHONY: install
install: ## Install CRDs into the K8s cluster specified in ~/.kube/config.
	kubectl apply -f odoo-operator/templates/crds/

.PHONY: uninstall
uninstall: ## Uninstall CRDs from the K8s cluster specified in ~/.kube/config.
	kubectl delete -f odoo-operator/templates/crds/

.PHONY: deploy
deploy: ## Deploy controller to the K8s cluster specified in ~/.kube/config.
	helm install odoo-operator ./odoo-operator

.PHONY: undeploy
undeploy: ## Undeploy controller from the K8s cluster specified in ~/.kube/config.
	helm uninstall odoo-operator

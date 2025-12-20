IMAGE ?= guerite
TAG ?= latest
FULL_IMAGE := $(IMAGE):$(TAG)

.PHONY: build tag-ghcr

build:
	docker build -t $(FULL_IMAGE) .

dual-tag: build
	docker tag $(FULL_IMAGE) ghcr.io/$(shell whoami)/$(IMAGE):$(TAG)

tag-ghcr: dual-tag


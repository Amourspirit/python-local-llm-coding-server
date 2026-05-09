include .env
export

ifndef MODEL_MAIN_PROFILE
$(error MODEL_MAIN_PROFILE is not set in .env)
endif
ifndef MODEL_DRAFT_PROFILE
$(error MODEL_DRAFT_PROFILE is not set in .env)
endif

define runtime_script
$(shell runtime=$$(grep '^runtime:' storage/project-local-config/profiles/models/$(1).yaml 2>/dev/null | awk '{print $$2}' | tr -d '\r'); \
	if [ "$$runtime" = "swiftlm" ]; then echo "scripts/swiftlm_profile.py"; \
	elif [ "$$runtime" = "mlx_vlm" ]; then echo "scripts/mlx_profile.py"; \
	else echo ""; fi)
endef

.PHONY: help \
	swift-list swift-show swift-start swift-status swift-stop swift-restart \
	mlx-list mlx-show mlx-start mlx-status mlx-stop mlx-restart \
	dev-show dev-status dev-start dev-stop dev-restart \
	test test-unit test-integration

PROFILE ?=
PYTHON ?= .venv/bin/python

help:
	@echo "SwiftLM profile commands:"
	@echo "  make swift-list"
	@echo "  make swift-show PROFILE=<profile_name>"
	@echo "  make swift-start PROFILE=<profile_name>"
	@echo "  make swift-status PROFILE=<profile_name>"
	@echo "  make swift-stop PROFILE=<profile_name>"
	@echo "  make swift-restart PROFILE=<profile_name>"
	@echo ""
	@echo "mlx_vlm profile commands:"
	@echo "  make mlx-list"
	@echo "  make mlx-show PROFILE=<profile_name>"
	@echo "  make mlx-start PROFILE=<profile_name>"
	@echo "  make mlx-status PROFILE=<profile_name>"
	@echo "  make mlx-stop PROFILE=<profile_name>"
	@echo "  make mlx-restart PROFILE=<profile_name>"
	@echo ""
	@echo "Dev Models commands (MODEL_MAIN_PROFILE + MODEL_DRAFT_PROFILE from .env):"
	@echo "  make dev-status   -- show status of both profiles"
	@echo "  make dev-start    -- start main, wait 5s, start draft"
	@echo "  make dev-stop     -- stop draft, then stop main"
	@echo "  make dev-restart  -- dev-stop then dev-start"
	@echo ""
	@echo "Test commands:"
	@echo "  make test"
	@echo "  make test-unit"
	@echo "  make test-integration"

swift-list:
	$(PYTHON) scripts/swiftlm_profile.py list

swift-show:
	$(PYTHON) scripts/swiftlm_profile.py show --profile $(PROFILE)

swift-start:
	$(PYTHON) scripts/swiftlm_profile.py start --profile $(PROFILE)

swift-status:
	$(PYTHON) scripts/swiftlm_profile.py status --profile $(PROFILE)

swift-stop:
	$(PYTHON) scripts/swiftlm_profile.py stop --profile $(PROFILE)

swift-restart:
	$(PYTHON) scripts/swiftlm_profile.py restart --profile $(PROFILE)

mlx-list:
	$(PYTHON) scripts/mlx_profile.py list

mlx-show:
	$(PYTHON) scripts/mlx_profile.py show --profile $(PROFILE)

mlx-start:
	$(PYTHON) scripts/mlx_profile.py start --profile $(PROFILE)

mlx-status:
	$(PYTHON) scripts/mlx_profile.py status --profile $(PROFILE)

mlx-stop:
	$(PYTHON) scripts/mlx_profile.py stop --profile $(PROFILE)

mlx-restart:
	$(PYTHON) scripts/mlx_profile.py restart --profile $(PROFILE)

# Dev Models — orchestrate MODEL_MAIN_PROFILE + MODEL_DRAFT_PROFILE together
DEV_MAIN_SCRIPT  := $(call runtime_script,$(MODEL_MAIN_PROFILE))
DEV_DRAFT_SCRIPT := $(call runtime_script,$(MODEL_DRAFT_PROFILE))

dev-status:
	@echo "=== Main Profile: $(MODEL_MAIN_PROFILE) ==="
	$(PYTHON) $(DEV_MAIN_SCRIPT) status --profile $(MODEL_MAIN_PROFILE)
	@echo ""
	@echo "=== Draft Profile: $(MODEL_DRAFT_PROFILE) ==="
	$(PYTHON) $(DEV_DRAFT_SCRIPT) status --profile $(MODEL_DRAFT_PROFILE)

dev-start:
	@echo "Starting main profile: $(MODEL_MAIN_PROFILE)"
	$(PYTHON) $(DEV_MAIN_SCRIPT) start --profile $(MODEL_MAIN_PROFILE)
	@echo "Waiting 5 seconds before starting draft profile..."
	@sleep 5
	@echo "Starting draft profile: $(MODEL_DRAFT_PROFILE)"
	$(PYTHON) $(DEV_DRAFT_SCRIPT) start --profile $(MODEL_DRAFT_PROFILE)

dev-stop:
	@echo "Stopping draft profile: $(MODEL_DRAFT_PROFILE)"
	$(PYTHON) $(DEV_DRAFT_SCRIPT) stop --profile $(MODEL_DRAFT_PROFILE)
	@echo "Stopping main profile: $(MODEL_MAIN_PROFILE)"
	$(PYTHON) $(DEV_MAIN_SCRIPT) stop --profile $(MODEL_MAIN_PROFILE)

dev-restart: dev-stop dev-start

test:
	$(PYTHON) -m pytest tests/

test-unit:
	$(PYTHON) -m pytest tests/unit -m unit

test-integration:
	$(PYTHON) -m pytest tests/integration -m integration

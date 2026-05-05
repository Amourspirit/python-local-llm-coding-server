.PHONY: help \
	swift-list swift-show swift-start swift-status swift-stop swift-restart \
	mlx-list mlx-show mlx-start mlx-status mlx-stop mlx-restart

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

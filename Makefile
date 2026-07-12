.PHONY: help install run update test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip3 install -r requirements.txt

run: ## Start the Metaphors server
	python3 server.py

update: ## Pull latest changes, refresh deps, run migrations
	python3 scripts/update.py

test: ## Run tests
	python3 -m pytest tests/ -v

clean: ## Clean up cache and temp files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

screenshot: ## Capture screenshot of running app
	python3 scripts/screenshot.py

screenshot-hd: ## Capture HD screenshot (1920x1080)
	python3 scripts/screenshot.py --width 1920 --height 1080

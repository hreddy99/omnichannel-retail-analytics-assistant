# Convenience targets. These delegate to tools.py (the cross-platform task
# runner) or call the package modules directly. Free/local stack only.

.PHONY: setup validate data catalog run test

setup:           ## Create the local venv and install dependencies
	python tools.py setup

data:            ## Regenerate the synthetic dataset and print row counts
	python -m data.generator

catalog:         ## Validate the governed YAML catalog (loads + hashes)
	python scripts/validate_catalog.py

validate:        ## Run the data-validation checks
	python -m evals.validation

test:            ## Run the unit / contract test suite
	python -m pytest

run:             ## Launch the Streamlit app
	python tools.py run

#
#	Configuration
#

PYTHON=python
REQUIREMENTS_ENGINE=pipenv


#
#	Variable Setup
#

GEN_REQUIREMENTS=pip freeze --local > requirements.txt

ifeq ($(REQUIREMENTS_ENGINE), pipenv)
	INSTALL_REQS_CMD=pipenv install
	RUN_PRE=pipenv run
	PYTHON := $(RUN_PRE) $(PYTHON)
	GEN_REQUIREMENTS := $(RUN_PRE) $(GEN_REQUIREMENTS)
else
	INSTALL_REQS_CMD=pip install -r requirements.txt
endif


#
#	Recipes
#

# - Setup related
.phony: requirements generate_requirements

requirements:
	$(INSTALL_REQS_CMD)

generate_requirements:
	$(GEN_REQUIREMENTS)

# - Data related
.phony: get_data continue_get_data process_data generate_features clear_data

get_data:
	@$(PYTHON) src/get_data.py nasa
	@$(PYTHON) src/get_data.py noaa
	@$(PYTHON) src/get_data.py wunderground

continue_get_data:
	@$(PYTHON) src/get_data.py wunderground --no-regions

process_data:
	@$(PYTHON) src/process_data.py wunderground
	@$(PYTHON) src/process_data.py nasa
	@$(PYTHON) src/process_data.py noaa

generate_features:
	@$(PYTHON) src/generate_features.py noaa

clear_data:
	@rm data/raw/*.pkl
	@rm data/raw/*.txt
	@rm data/raw/*.csv
	@rm data/raw/*.zip
	@rm data/processed/*.pkl
	@rm data/features/*.pkl

# - Media Related
.phony: clear_media

clear_media:
	@rm media/*.*

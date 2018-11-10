#
#	Configuration
#

PYTHON=python
REQUIREMENTS_ENGINE=pipenv


#
#	Variable Setup
#

ifeq ($(REQUIREMENTS_ENGINE), pipenv)
	INSTALL_REQS_CMD=pipenv install
	PYTHON_RUN=pipenv run $(PYTHON)
else
	INSTALL_REQS_CMD=pip install -r requirements.txt
endif


#
#	Recipes
#

# - Setup related
.phony: requirements

requirements:
	$(INSTALL_REQS_CMD)

# - Data related
.phony: get_data continue_get_data process_data clear_data

get_data:
	$(PYTHON_RUN) src/get_data.py nasa
	$(PYTHON_RUN) src/get_data.py wunderground

continue_get_data:
	$(PYTHON_RUN) src/get_data.py wunderground --no-regions --no-years

process_data:
	$(PYTHON_RUN) src/process_data wunderground

clear_data:
	rm data/raw/*.pkl
	rm data/raw/*.txt
	rm data/processed/*.pkl

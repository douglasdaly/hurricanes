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
	PYTHON=pipenv run $(PYTHON)
else
	INSTALL_REQS_CMD=pip install -r requirements.txt
endif


#
#	Recipes
#

.phony: requirements get_data process_data

requirements:
	$(INSTALL_REQS_CMD)

get_data:
	$(PYTHON) src/get_data.py wunderground
	$(PYTHON) src/get_data.py nasa

process_data:
	$(PYTHON) src/process_data wunderground

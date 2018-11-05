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
.phony: requirements data

requirements:
	$(INSTALL_REQS_CMD)

data:
	$(PYTHON) /src/get_data.py
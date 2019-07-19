#
#	Configuration
#

PYTHON=python
REQUIREMENTS_ENGINE=pipenv


#
#	Setup
#

GEN_REQUIREMENTS=pip freeze --local > requirements.txt

ifeq ($(REQUIREMENTS_ENGINE), pipenv)
	RUN_PRE = pipenv run
	INSTALL_REQS_CMD = pipenv install
	GEN_REQUIREMENTS = pipenv lock -r > requirements.txt
else
	RUN_PRE = 
	INSTALL_REQS_CMD = pip install -r requirements.txt
endif

PYTHON := $(RUN_PRE) $(PYTHON)


#
#	Recipes
#

.PHONY: help requirements generate_requirements \
		get_data continue_get_data process_data generate_features \
		clear_raw_data clear_processed_data clear_features_data clear_data \
		clear_media generate_media

.DEFAULT_GOAL := help

# - Setup related

help: ## Prints help for this Makefile
	@printf 'Usage: make \033[36m[target]\033[0m\n'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo ''

requirements: ## Installs requirements for this project
	$(INSTALL_REQS_CMD)

generate_requirements: ## Generates requirements.txt for this project
	$(GEN_REQUIREMENTS)

get_data: clear_raw_data ## Downloads data from the web for this project
	@echo "[INFO] Getting raw data files..."
	@$(PYTHON) src/get_data.py nasa
	@$(PYTHON) src/get_data.py noaa
	@$(PYTHON) src/get_data.py wunderground

continue_get_data:  ## Continues downloading data (if timed out or blocked)
	@echo "[INFO] Continuing to get raw data files..."
	@$(PYTHON) src/get_data.py wunderground --no-regions

process_data: clear_processed_data  ## Processes download data for use
	@echo "[INFO] Processing raw data files..."
	@$(PYTHON) src/process_data.py wunderground
	@$(PYTHON) src/process_data.py nasa
	@$(PYTHON) src/process_data.py noaa

generate_features: clear_features_data  ## Generates features from processed data
	@echo "[INFO] Generating features data files..."
	@$(PYTHON) src/generate_features.py noaa interpolate

# - Cleaning related

clear_data: clear_raw_data clear_processed_data clear_features_data  ## Clears out all data for this project

clear_features_data:  ## Clears out features data files
	@echo "[INFO] Clearing features data files..."
	@rm -f data/features/*.pkl || true

clear_processed_data:  ## Clears out processed data files
	@echo "[INFO] Clearing processed data files..."
	@rm -f data/processed/*.pkl || true

clear_raw_data:  ## Clears out raw data files
	@echo "[INFO] Clearing raw data files..."
	@rm -f data/raw/*.pkl || true
	@rm -f data/raw/*.txt || true
	@rm -f data/raw/*.csv || true
	@rm -f data/raw/*.zip || true

# - Media Related

clear_media:  ## Clears out media files for this project
	@echo "[INFO] Clearing existing media..."
	@rm -f media/*.* || true
	@rm -f logs/generate_media/*.* || true

generate_media: clear_media  ## Generates media files for this project
	@echo "[INFO] Generating media from notebook files..."
	@$(PYTHON) src/generate_media.py notebook notebooks/2_wunderground_processed_data_research.ipynb
	@$(PYTHON) src/generate_media.py notebook notebooks/4_nasa_processed_data_research.ipynb
	@$(PYTHON) src/generate_media.py notebook notebooks/6_noaa_interpolated_feature_data_explore.ipynb
	@$(PYTHON) src/generate_media.py notebook notebooks/7_mcmc_model.ipynb
	@echo "[INFO] Generating animated global heatmaps..."
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3.5 --dpi 72 globe data/features/noaa_surface_interpolated_data.pkl --output media/interp_animated_surface.mp4 --title "Surface Temperature Anomaly" --animate --compress --use-optimage --percentile 15 --fps 4 --smooth 12 --end-index 2018
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3.5 --dpi 72 globe data/features/noaa_aloft_interpolated_data.pkl --output media/interp_animated_aloft.mp4 --title "Aloft Temperature Anomaly" --animate --compress --use-optimage --percentile 15 --fps 4 --smooth 12 --end-index 2018
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3.5 --dpi 72 globe data/features/noaa_diff_interpolated_data.pkl --output media/interp_animated_diff.mp4 --title "Surface - Aloft Differential" --animate --compress --use-optimage --percentile 15 --fps 4 --smooth 12 --end-index 2018
	@echo "[INFO] Generating static global heatmaps..."
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_surface_interpolated_data.pkl --output media/interp_1965_surface.png --title "Surface Temperature Anomaly" --percentile 15 --smooth 12 --index 1965 --show-colorbar --colorbar-label "Degrees Celsius"
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_surface_interpolated_data.pkl --output media/interp_2017_surface.png --title "Surface Temperature Anomaly" --percentile 15 --smooth 12 --index 2017 --show-colorbar --colorbar-label "Degrees Celsius"
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_aloft_interpolated_data.pkl --output media/interp_1965_aloft.png --title "Aloft Temperature Anomaly" --percentile 15 --smooth 12 --index 1965 --show-colorbar --colorbar-label "Degrees Celsius"
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_aloft_interpolated_data.pkl --output media/interp_2017_aloft.png --title "Aloft Temperature Anomaly" --percentile 15 --smooth 12 --index 2017 --show-colorbar --colorbar-label "Degrees Celsius"
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_diff_interpolated_data.pkl --output media/interp_1965_diff.png --title "Surface - Aloft Differential" --percentile 15 --smooth 12 --index 1965 --show-colorbar --colorbar-label "Degrees Celsius"
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_diff_interpolated_data.pkl --output media/interp_2017_diff.png --title "Surface - Aloft Differential" --percentile 15 --smooth 12 --index 2017 --show-colorbar --colorbar-label "Degrees Celsius"

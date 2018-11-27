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
.phony: get_data continue_get_data process_data generate_features

get_data: clear_raw_data
	@echo "[INFO] Getting raw data files..."
	@$(PYTHON) src/get_data.py nasa
	@$(PYTHON) src/get_data.py noaa
	@$(PYTHON) src/get_data.py wunderground

continue_get_data:
	@echo "[INFO] Continuing to get raw data files..."
	@$(PYTHON) src/get_data.py wunderground --no-regions

process_data: clear_processed_data
	@echo "[INFO] Processing raw data files..."
	@$(PYTHON) src/process_data.py wunderground
	@$(PYTHON) src/process_data.py nasa
	@$(PYTHON) src/process_data.py noaa

generate_features: clear_features_data
	@echo "[INFO] Generating features data files..."
	@$(PYTHON) src/generate_features.py noaa interpolate

# - Cleaning related
.phony: clear_raw_data clear_processed_data clear_features_data clear_data

clear_data: clear_raw_data clear_processed_data clear_features_data

clear_features_data:
	@echo "[INFO] Clearing features data files..."
	@rm data/features/*.pkl || true

clear_processed_data:
	@echo "[INFO] Clearing processed data files..."
	@rm data/processed/*.pkl || true

clear_raw_data:
	@echo "[INFO] Clearing raw data files..."
	@rm data/raw/*.pkl || true
	@rm data/raw/*.txt || true
	@rm data/raw/*.csv || true
	@rm data/raw/*.zip || true

# - Media Related
.phony: clear_media generate_media test_media

clear_media:
	@echo "[INFO] Clearing existing media..."
	@rm media/*.* || true
	@rm logs/generate_media/*.* || true

generate_media: clear_media
	@echo "[INFO] Generating media from notebook files..."
	@$(PYTHON) src/generate_media.py notebook notebooks/2_wunderground_processed_data_research.ipynb
	@$(PYTHON) src/generate_media.py notebook notebooks/4_nasa_processed_data_research.ipynb
	@$(PYTHON) src/generate_media.py notebook notebooks/6_noaa_interpolated_feature_data_explore.ipynb
	@echo "[INFO] Generating animated global heatmaps..."
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3.5 --dpi 72 globe data/features/noaa_surface_interpolated_data.pkl --output media/interp_animated_surface.gif --title "Surface Temperature Anomaly" --animate --compress --use-optimage --percentile 15 --fps 4 --smooth 12 --end-index 2018
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3.5 --dpi 72 globe data/features/noaa_aloft_interpolated_data.pkl --output media/interp_animated_aloft.gif --title "Aloft Temperature Anomaly" --animate --compress --use-optimage --percentile 15 --fps 4 --smooth 12 --end-index 2018
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3.5 --dpi 72 globe data/features/noaa_diff_interpolated_data.pkl --output media/interp_animated_diff.gif --title "Surface - Aloft Differential" --animate --compress --use-optimage --percentile 15 --fps 4 --smooth 12 --end-index 2018
	@echo "[INFO] Generating static global heatmaps..."
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_surface_interpolated_data.pkl --output media/interp_1965_surface.png --title "Surface Temperature Anomaly" --percentile 15 --smooth 12 --index 1965 --show-colorbar --colorbar-label "Degrees Celsius"
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_surface_interpolated_data.pkl --output media/interp_2017_surface.png --title "Surface Temperature Anomaly" --percentile 15 --smooth 12 --index 2017 --show-colorbar --colorbar-label "Degrees Celsius"
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_aloft_interpolated_data.pkl --output media/interp_1965_aloft.png --title "Aloft Temperature Anomaly" --percentile 15 --smooth 12 --index 1965 --show-colorbar --colorbar-label "Degrees Celsius"
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_aloft_interpolated_data.pkl --output media/interp_2017_aloft.png --title "Aloft Temperature Anomaly" --percentile 15 --smooth 12 --index 2017 --show-colorbar --colorbar-label "Degrees Celsius"
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_diff_interpolated_data.pkl --output media/interp_1965_diff.png --title "Surface - Aloft Differential" --percentile 15 --smooth 12 --index 1965 --show-colorbar --colorbar-label "Degrees Celsius"
	@$(PYTHON) src/generate_media.py heatmap --figsize-width 6 --figsize-height 3 --dpi 72 globe data/features/noaa_diff_interpolated_data.pkl --output media/interp_2017_diff.png --title "Surface - Aloft Differential" --percentile 15 --smooth 12 --index 2017 --show-colorbar --colorbar-label "Degrees Celsius"
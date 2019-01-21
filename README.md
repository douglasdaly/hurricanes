# Hurricane Data Analysis

*An analysis of historical tropical cyclone data from Weather Underground and global climate data from NASA and NOAA.*

-----

## Prerequisites

For the cartopy package you'll need to have installed the [GEOS](https://trac.osgeo.org/geos/) and [PROJ](https://proj4.org/) libraries.  On linux the packages are:

 - `libproj-dev`
 - `proj-data`
 - `proj-bin`
 - `libgeos-dev`


## Setup

Configure your options in the ```Makefile```, specifically the ```REQUIREMENTS_ENGINE``` variable (either ```pip``` or ```pipenv```).  Also, if your default system ```python``` is not Python 3 you'll want to change the ```PYTHON``` variable to match the command for Python 3 (likely ```python3``` on *nix systems).

To install the requirements needed for the project:

```bash
$ make requirements
```

## Data

### Raw Data

Once you've configured your environment, you can download the raw data using:

```bash
$ make get_data
```

Though this will likely fail on the storm data (Weather Underground will probably cut you off after too many requests).  To continue updating storm data, periodically run:

```bash
$ make continue_get_data
```

Until you see the output:

> ```Pulling storm data... DONE```

The NASA and NOAA data will download before the Weather Underground data and should not be a problem.  The tool [```get_data```](./src/get_data.py) is utilized for all of this.  See that tool for further information.

### Processed Data

Once you've downloaded the raw data files you can run:

```bash
$ make process_data
```

To process the raw data and save local copies of the (lightly) processed data to local ```.pkl``` files for further research.  The tool [```process_data```](./src/process_data.py) is utilized for this.  See that tool for further information.

### Feature Data

Once the data has been processed you can then generate some of the more interesting and further-processed feature data with the command:

```bash
$ make generate_features
```

The tool [```generate_features```](./src/generate_features.py) is utilized to do this.  See that tool for further information.

Note: This could be time-consuming depending upon your system.  There's an interpolation calculation on the NOAA temperature data which is fairly heavy computationally (the code is designed to take advantage of multi-core systems).

## Media

Once you've run all the preceding commands in the Data section, you can generate various media files for the project:

```bash
$ make generate_media
```

The tool [```generate_media```](./src/generate_media.py) is utilized to do this.  See that tool for further information.

Note: This may require additional dependencies (like [pngcrush](https://pmt.sourceforge.io/pngcrush/), [optipng](http://optipng.sourceforge.net/) and [zopfli](https://github.com/google/zopfli)) if certain compression features are utilized.  You may also want to have [ImageMagick](https://www.imagemagick.org/script/index.php) installed as that can generate nicer GIF images.


## License

This project's code is licensed under the MIT license.  See the `LICENSE` file for more information.

Data for this project was acquired from the [Weather Underground](https://www.wunderground.com/) website, [NASA](https://climate.nasa.gov/) and [NOAA](https://www.ncdc.noaa.gov/).

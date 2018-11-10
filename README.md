# Hurricane Data Analysis

*An analysis of historical hurricane/cyclone data from Weather Underground.*

-----

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


### Processed Data

Once you've downloaded the raw data files you can run:

```bash
$ make process_data
```

To process the raw data and save local copies.


## License

This project's code is licensed under the MIT license.  See the `LICENSE` file for more information.

Data for this project was acquired from the (https://www.weatherunderground.com/)[Weather Underground] website.

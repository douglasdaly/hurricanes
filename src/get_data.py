#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
get_data.py

    Script to download Weather Underground Hurricane data

@author: Douglas Daly
@date: 11/4/2018
"""
#
#   Imports
#
import os
import re
import time
import pickle
import urllib.request
from datetime import datetime

import click
from bs4 import BeautifulSoup


#
#   Variables
#

# - Weather Underground
region_list_url = "https://www.wunderground.com/hurricane/hurrarchive.asp?region={}"
ind_data_url = "https://www.wunderground.com/hurricane/{}{}.asp"
ind_storm_url = "https://www.wunderground.com/hurricane/{}{}{}.asp"

region_dict = {
        "North Atlantic": 'at',
        "East Pacific": 'ep',
        "Western Pacific": 'wp',
        "Indian Ocean": 'si'
}

# - NASA Data
nasa_temp_anomaly = 'http://climate.nasa.gov/system/internal_resources/details/original/647_Global_Temperature_Data_File.txt'
nasa_sea_level = 'ftp://podaac.jpl.nasa.gov/allData/merged_alt/L2/TP_J1_OSTM/global_mean_sea_level/GMSL_TPJAOS_4.2_199209_201807.txt'
nasa_co2_data = 'ftp://aftp.cmdl.noaa.gov/products/trends/co2/co2_mm_mlo.txt'

sea_surface_temp_main = 'https://neo.sci.gsfc.nasa.gov/view.php?datasetId=MYD28M&year={}'
nasa_sea_surface_temp = 'http://neo.sci.gsfc.nasa.gov/servlet/RenderData?si={}&cs=rgb&format=CSV&width=360&height=180'

# - NOAA Data
noaa_ratpac_b_url = "https://www1.ncdc.noaa.gov/pub/data/ratpac/ratpac-b/RATPAC-B-monthly-combined.txt.zip"
noaa_ratpac_stations_url = "https://www1.ncdc.noaa.gov/pub/data/ratpac/ratpac-stations.txt"


#
#   Functions
#

def get_data(url, retries=3):
    """Downloads object from the given URL"""
    if retries <= 0:
        raise Exception('Maximum retry count exceeded')

    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
    except urllib.request.HTTPError:
        time.sleep(3)
        return get_data(url, retries-1)

    return data


def get_soup(url):
    """Gets BS object from the given URL"""
    # - Get Data
    html = get_data(url)

    # - Get Soup
    soup = BeautifulSoup(html, 'html.parser')

    if soup is None:
        raise Exception("No data from URL")

    return soup


def get_region_page_data(region_code):
    """Processes a region main page"""
    url = region_list_url.format(region_code)
    soup = get_soup(url)
    data_tbl = soup.find(id='yearList')

    col_idxs = ['Year', 'Storms', 'Hurricanes', 'Deaths', 'Damage']
    ret = dict()
    for row in data_tbl.find_all('tr'):
        cols = row.find_all('td')
        if cols is None or len(cols) == 0:
            continue

        t_data = dict()
        for i_col in range(1, len(col_idxs)):
            col = cols[i_col]
            t_data[col_idxs[i_col]] = col.text.strip()
        yr = int(cols[0].text.strip())
        ret[yr] = t_data

    return ret


def get_year_page_data(region_code, year):
    """Get data for single year"""
    url = ind_data_url.format(region_code, year)
    soup = get_soup(url)
    storm_tbl = soup.find(id="stormList").find('tbody')

    col_idxs = ['Storm', 'Dates', 'Max Winds', 'Min Pressure', 'Deaths',
                'Damage', 'US Landfall Category']
    ret = dict()
    for row in storm_tbl.find_all('tr'):
        cols = row.find_all('td')
        if cols is None or len(cols) == 0:
            continue

        t_data = dict()
        for i_col in range(len(cols)):
            col = cols[i_col]
            t_data[col_idxs[i_col]] = col.text.strip()

        id_str = cols[0].find('a').attrs['href'].split('/')[-1].split('.')[0]
        id_no = int(id_str.replace('{}{}'.format(region_code, year), ''))
        ret[id_no] = t_data

    return ret


def get_storm_page_data(region_code, year, storm_id):
    """Gets data for a single storm"""
    url = ind_storm_url.format(region_code, year, storm_id)
    soup = get_soup(url)
    path_tbl = soup.find(id="stormList").find('tbody')

    col_idxs = ['Date', 'Time', 'Lat', 'Lon', 'Wind', 'Pressure', 'Storm Type']
    ret = list()
    for row in path_tbl.find_all('tr'):
        cols = row.find_all('td')
        if cols is None or len(cols) == 0:
            continue

        t_data = dict()
        for i_col in range(len(col_idxs)):
            col = cols[i_col]
            t_data[col_idxs[i_col]] = col.text.strip()

        ret.append(t_data)

    return ret


# - NASA

def get_sea_surface_file_codes_for_year(year):
    """Helper to get file codes for given calendar year"""
    url = sea_surface_temp_main.format(year)
    soup = get_soup(url)

    p_code = re.compile("\('([0-9]\w+)'")
    p_date = re.compile("'([0-9]+-[0-9]+-[0-9]+)'")

    codes = dict()

    month_selects = soup.findAll('div', class_='slider-elem month')
    for ms in month_selects:
        t_js = ms.find('a').attrs['onclick']

        t_code = p_code.findall(t_js)
        t_date = p_date.findall(t_js)

        if len(t_code) == 1 and len(t_date) == 1:
            codes[datetime.strptime(t_date[0], '%Y-%m-%d').date()] = t_code[0]

    return codes


#
#   Main Script Functions
#

@click.group()
@click.pass_context
def cli(ctx):
    """Functions to get various pieces of weather-related data"""
    ctx.ensure_object(dict)


@cli.command()
@click.pass_context
@click.option('--regions/--no-regions', default=True,
              help='Whether or not to pull top-level region data')
@click.option('--years/--no-years', default=True,
              help='Whether or not to pull year-level storm data')
@click.option('--storms/--no-storms', default=True,
              help='Whether or not to pull individual storm data')
def wunderground(ctx, regions, years, storms):
    """Weather Underground data pull function"""
    # - Regions
    if regions:
        print('Pulling region data... ', end='', flush=True)
        region_data = dict()
        for region, region_code in region_dict.items():
            t_data = get_region_page_data(region_code)
            region_data[region] = t_data

        with open('data/raw/region_data.pkl', 'wb') as fout:
            pickle.dump(region_data, fout)
        print('DONE')

    else:
        with open('data/raw/region_data.pkl', 'rb') as fin:
            region_data = pickle.load(fin)
        print('Region data loaded')

    # - Years
    if years:
        if os.path.isfile('data/raw/region_year_data.pkl'):
            print('Loading saved region year data... ', end='', flush=True)
            with open('data/raw/region_year_data.pkl', 'rb') as fin:
                region_year_data = pickle.load(fin)
            print('DONE')
        else:
            region_year_data = dict()

        print('Pulling yearly data... ', end='', flush=True)
        try:
            for region, region_meta in region_data.items():
                region_year_data[region] = dict()
                for year, yr_meta in region_meta.items():
                    if year in region_year_data[region].keys():
                        continue

                    n_strms = yr_meta['Storms']
                    if n_strms is None or n_strms.strip() == '' or int(n_strms) == 0:
                        continue

                    y_data = get_year_page_data(region_dict[region], year)
                    region_year_data[region][year] = y_data
        except Exception as ex:
            print('ERROR')
            print("  Unable to get all yearly data: ")
            print("\t", end='')
            print(ex)

        with open('data/raw/region_year_data.pkl', 'wb') as fout:
            pickle.dump(region_year_data, fout)
        print('DONE')

    else:
        with open('data/raw/region_year_data.pkl', 'rb') as fin:
            region_year_data = pickle.load(fin)
        print('Year data loaded')

    # - Storms
    if storms:
        if os.path.isfile('data/raw/storm_data.pkl'):
            print('Loading saved storm data... ', end='', flush=True)
            with open('data/raw/storm_data.pkl', 'rb') as fin:
                storm_data = pickle.load(fin)
            print('DONE')
        else:
            storm_data = dict()

        print('Pulling storm data... ', end='', flush=True)
        try:
            for region, reg_yr_data in region_year_data.items():
                storm_data[region] = dict()
                for yr, yr_data in reg_yr_data.items():
                    storm_data[region][yr] = dict()
                    for storm_id in yr_data.keys():
                        if storm_id in storm_data[region][yr].keys():
                            continue
                        t_data = get_storm_page_data(region_dict[region], yr,
                                                     storm_id)
                        storm_data[region][yr][storm_id] = t_data
            print('DONE')

        except Exception as ex:
            print('ERROR')
            print("  Unable to get all storm data: ")
            print("\t", end='')
            print(ex)

        print('Saving storm data... ', end='', flush=True)
        with open('data/raw/storm_data.pkl', 'wb') as fout:
            pickle.dump(storm_data, fout)
        print('DONE')
    else:
        print('Skipping storms data')


@cli.command()
@click.pass_context
def nasa(ctx):
    """Gets global temperature data from NASA"""
    # - Misc. Global Temperature Data
    links = {
        'Temperature anomaly': (nasa_temp_anomaly, 'nasa_temperature_anomaly.txt'),
        'Global sea-level': (nasa_sea_level, 'nasa_sea_level.txt'),
        'Carbon Dioxide level': (nasa_co2_data, 'nasa_carbon_dioxide_levels.txt')
    }

    for name, (link, output) in links.items():
        print('Downloading NASA {} data... '.format(name), end='', flush=True)
        temp_txt = get_data(link)

        with open('data/raw/{}'.format(output), 'wb') as fout:
            fout.write(temp_txt)
        print('DONE')

    # - Sea Surface Temperature Data
    print('Getting NASA Sea-Surface Temperature file names... ', end='', flush=True)
    all_codes = dict()
    for yr in range(2002, datetime.today().year+1):
        t_codes = get_sea_surface_file_codes_for_year(yr)
        if t_codes is not None and len(t_codes) > 0:
            all_codes = {**all_codes, **t_codes}
    print('DONE')

    for dt, code in all_codes.items():
        print('Downloading Sea Surface Temp data for {}... '.format(dt), end='', flush=True)
        t_data = get_data(nasa_sea_surface_temp.format(code))
        with open('data/raw/nasa_sea_temp_{}.csv'.format(dt.strftime('%Y%m%d')), 'wb') as fout:
            fout.write(t_data)
        print('DONE')

@cli.command()
@click.pass_context
def noaa(ctx):
    """Gets stratosphere temperature data from NOAA"""
    # - NOAA RATPAC Data
    print('Downloading NOAA RATPAC station data... ', end='', flush=True)
    t_data = get_data(noaa_ratpac_stations_url)
    with open('data/raw/ratpac_stations.txt', 'wb') as fout:
        fout.write(t_data)
    print('DONE')

    print('Downloading NOAA RATPAC-B data... ', end='', flush=True)
    t_data = get_data(noaa_ratpac_b_url)
    with open('data/raw/ratpac_b.zip', 'wb') as fout:
        fout.write(t_data)
    print('DONE')


#
#   Entry-point
#

if __name__ == "__main__":
    """Script entry-point"""
    cli(obj={})

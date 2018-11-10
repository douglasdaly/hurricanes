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
import time
import pickle
import urllib.request

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
        "Indian Ocean": 'is'
}

# - NASA Temperature Data
nasa_temp_anomaly = 'http://climate.nasa.gov/system/internal_resources/details/original/647_Global_Temperature_Data_File.txt'
nasa_sea_level = 'ftp://podaac.jpl.nasa.gov/allData/merged_alt/L2/TP_J1_OSTM/global_mean_sea_level/GMSL_TPJAOS_4.2_199209_201807.txt'
nasa_co2_data = 'ftp://aftp.cmdl.noaa.gov/products/trends/co2/co2_mm_mlo.txt'

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
        return get_file(url, retries-1)

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
        print('Pulling region data...')
        region_data = dict()
        for region, region_code in region_dict.items():
            t_data = get_region_page_data(region_code)
            region_data[region] = t_data

        with open('data/raw/region_data.pkl', 'wb') as fout:
            pickle.dump(region_data, fout)
        print('Region data saved')
    else:
        with open('data/raw/region_data.pkl', 'rb') as fin:
            region_data = pickle.load(fin)
        print('Region data loaded')

    # - Years
    if years:
        print('Pulling yearly data...')
        region_year_data = dict()
        for region, region_meta in region_data.items():
            region_year_data[region] = dict()
            for year, yr_meta in region_meta.items():
                n_strms = yr_meta['Hurricanes']
                if n_strms is None or n_strms.strip() == '' or int(n_strms) == 0:
                    continue

                y_data = get_year_page_data(regions[region], year)
                region_year_data[region][year] = y_data

        with open('data/raw/region_year_data.pkl', 'wb') as fout:
            pickle.dump(region_year_data, fout)
        print('Year data saved')
    else:
        with open('data/raw/region_year_data.pkl', 'rb') as fin:
            region_year_data = pickle.load(fin)
        print('Year data loaded')

    # - Storms
    if storms:
        if os.path.isfile('data/raw/storm_data.pkl'):
            with open('data/raw/storm_data.pkl', 'rb') as fin:
                storm_data = pickle.load(fin)
            print('Storm data loaded')
        else:
            storm_data = dict()

        print('Pulling storm data...')
        try:
            for region, reg_yr_data in region_year_data.items():
                storm_data[region] = dict()
                for yr, yr_data in reg_yr_data.items():
                    storm_data[region][yr] = dict()
                    for storm_id in yr_data.keys():
                        if storm_id in storm_data[region][yr].keys():
                            continue
                        t_data = get_storm_page_data(regions[region], yr,
                                                     storm_id)
                        storm_data[region][yr][storm_id] = t_data

        except Exception as ex:
            print("Unable to get all storm data: ")
            print(ex)

        with open('data/raw/storm_data.pkl', 'wb') as fout:
            pickle.dump(storm_data, fout)
        print('Storm data saved')
    else:
        print('Skipping storms data')


@cli.command()
def nasa():
    """Gets global temperature data from NASA"""
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


#
#   Entry-point
#

if __name__ == "__main__":
    """Script entry-point"""
    cli(obj={})

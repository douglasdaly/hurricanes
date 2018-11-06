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
region_list_url = "https://www.wunderground.com/hurricane/hurrarchive.asp?region={}"
ind_data_url = "https://www.wunderground.com/hurricane/{}{}.asp"
ind_storm_url = "https://www.wunderground.com/hurricane/{}{}{}.asp"

regions = {
        "North Atlantic": 'at',
        "East Pacific": 'ep',
        "Western Pacific": 'wp',
        "Indian Ocean": 'is'
}


#
#   Functions
#

def get_soup(url, retries=3):
    """Gets BS object from the given URL"""
    # - Get Data
    if retries <= 0:
        raise Exception('Maximum retry count exceeded')

    try:
        with urllib.request.urlopen(url) as response:
            html = response.read()
    except urllib.request.HTTPError:
        time.sleep(3)
        return get_soup(url, retries-1)

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

    col_idxs = ['Storms', 'Hurricanes', 'Deaths', 'Damage']
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
#   Main Script Code
#

@click.command()
@click.option('--region', 'pull_region', flag_value=True, default=True)
@click.option('--no-region', 'pull_region', flag_value=False)
@click.option('--years', 'pull_years', flag_value=True, default=True)
@click.option('--no-year', 'pull_years', flag_value=False)
@click.option('--storms', 'pull_storms', flag_value=True)
@click.option('--no-storms', 'pull_storms', flag_value=False, default=True)
def main(pull_region=True, pull_years=True, pull_storms=False):
    """Main script function"""
    # - Regions
    if pull_region:
        print('Pulling region data...')
        region_data = dict()
        for region, region_code in regions.items():
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
    if pull_years:
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
    if pull_storms:
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


if __name__ == "__main__":
    """Script entry-point"""
    main()

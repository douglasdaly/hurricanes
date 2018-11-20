#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
process_data.py

    Script to process Raw weather data

@author: Douglas Daly
@date: 11/10/2018
"""
#
#   Imports
#
import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

import click


#
#   Variables
#
raw_data_dir = "data/raw"
proc_data_dir = "data/processed"


#
#   Functions
#

def get_raw_wunderground_data(raw_dir):
    """Loads the raw Weather Underground data"""
    fnames = __get_file_names_helper(raw_dir, 'pkl')

    raw_data = dict()
    for k, v in fnames.items():
        with open(v, 'rb') as fin:
            raw_data[k] = pickle.load(fin)

    return raw_data


def __get_file_names_helper(directory, ext):
    """Loads raw NASA txt file data"""
    fnames = dict([(x.split('.')[0], os.path.join(directory, x))
                   for x in os.listdir(directory) if x.endswith(ext)])
    return fnames


# - Region Data Processing Functions

def __convert_region_data_helper(x):
    """Helper function to convert region data"""
    if x == '':
        return np.nan
    else:
        repl_strings = [',', '>', '<', '+']
        for rstr in repl_strings:
            x = x.replace(rstr, '')
        return float(x)


def __convert_region_data(data_dict):
    """Function to convert raw Region data"""
    ret = dict()
    for k, v in data_dict.items():
        ret[k] = __convert_region_data_helper(v)
    return ret


def process_region_data(raw_data):
    """Function to process raw Weather Underground regional data"""
    region_df = None
    for region, region_data in raw_data['region_data'].items():
        conv_data = dict()
        for k, v in region_data.items():
            conv_data[k] = __convert_region_data(v)
        t_region_df = pd.DataFrame(conv_data).T
        for col in t_region_df.columns:
            t_region_df[col] = t_region_df[col].astype(float)
        t_region_df.columns = pd.MultiIndex.from_product([[region], t_region_df.columns],
                                                         names=['Region', 'Statistic'])
        if region_df is None:
            region_df = t_region_df.copy()
        else:
            region_df = pd.concat([region_df, t_region_df], axis=1)

    region_df.sort_index(inplace=True)

    return region_df


# - Region-Year Data Processing
def __process_region_year_data_helper(year, k, v):
    """Helper function to process region-year data"""
    numeric_flds = ['Max Winds', 'Min Pressure', 'Deaths', 'Damage']
    if k == 'Storm':
        return v
    elif k == 'Dates':
        spl_dts = v.replace('-', ' ').split(' ')
        ret = list()
        for dt in spl_dts:
            t_dt = dt.strip()
            if t_dt == '' or t_dt.startswith('999'):
                continue

            sub_spl_dts = t_dt.split('/')
            sub_spl_dts[0] = np.mod(int(sub_spl_dts[0]), 13)
            if sub_spl_dts[0] == 0:
                sub_spl_dts[0] = 1

            str_dts = ["/{}".format(x) for x in sub_spl_dts]

            str_dt = str(year)+''.join(str_dts)
            try:
                t_dtime = datetime.strptime(str_dt, '%Y/%m/%d')
            except ValueError:
                str_dt = "{}/{}/1".format(year, sub_spl_dts[0]+1)
                t_dtime = datetime.strptime(str_dt, '%Y/%m/%d') - timedelta(days=1)

            ret.append(t_dtime)

        ret_names = ['Start Date', 'End Date']
        ret_dict = dict()
        for i in range(len(ret)):
            ret_dict[ret_names[i]] = ret[i]

        return ret_dict

    elif k in numeric_flds:
        if v == '' or v == 'Unknown':
            return np.nan
        elif v == 'Minimal':
            return 0.
        elif v == 'Millions':
            return 1000000.
        else:
            strip_chars = [',', '>', '<', '+']
            t_v = v
            for x in strip_chars:
                t_v = t_v.replace(x, '')

            ret = float(t_v)
            if ret == 9999.:
                ret = np.nan
            return ret

    else:
        return v

def __process_region_year_data(region, year, storm_id, storm_data):
    """Processes year-data to get storms"""
    unq_id = ''.join([x[0].upper() for x in region.split(' ')])
    unq_id += '{}{:02}'.format(year, storm_id)

    ret_data = dict()
    ret_data['Region'] = region
    for k, v in storm_data.items():
        try:
            t_ret_data = __process_region_year_data_helper(year, k, v)
            if isinstance(t_ret_data, dict):
                ret_data = {**ret_data, **t_ret_data}
            else:
                ret_data[k] = t_ret_data
        except Exception as ex:
            print(k, v)
            raise ex

    return unq_id, ret_data


def process_region_yearly_data(raw_data):
    """Processes Region-Year Weather Underground data"""
    storm_year_data = dict()
    for region, year_data in raw_data['region_year_data'].items():
        for yr, data in year_data.items():
            for t_storm_id, t_storm_data in data.items():
                t_id, t_data = __process_region_year_data(region, yr, t_storm_id,
                                                          t_storm_data)
                storm_year_data[t_id] = t_data

    storm_year_df = None
    for k, v in storm_year_data.items():
        t_df = pd.DataFrame(v, index=[k])

        if storm_year_df is None:
            storm_year_df = t_df
        else:
            storm_year_df = pd.concat([storm_year_df, t_df], axis=0, sort=False)

    storm_year_df.index.name = 'StormID'
    storm_year_df.sort_values('Start Date', axis=0, inplace=True)

    return storm_year_df


def __process_single_track_point(data_dict):
    """Helper function to process single track data point"""
    key_dt = None
    key_tm = None
    vals = dict()

    for k, v in data_dict.items():
        if k == 'Date':
            try:
                _ = int(v[0])
                key_dt = datetime.strptime(v, '%m/%d/%Y').date()
            except Exception:
                key_dt = datetime.strptime(v, '%b/%d/%Y').date()

        elif k == 'Time':
            if len(v.split(' ')[0]) > 2:
                key_tm = datetime.strptime(v, '%H%M %Z').time()
            else:
                key_tm = datetime.strptime(v, '%H %Z').time()

        elif k == 'Storm Type':
            vals[k] = v

        else:
            if v == 'Unknown':
                t_v = np.nan
            else:
                t_v = float(v)

            vals[k] = t_v

    return datetime.combine(key_dt, key_tm), vals


def __process_storm_track_data_points(region, year, storm_id, track_data):
    """Helper function to process track data points"""
    storm_code = ''.join([x[0] for x in region.upper().split(' ')])
    storm_code += '{}{:02d}'.format(year, storm_id)

    ret = dict()
    for data_point in track_data:
        try:
            fmt_date, fmt_data = __process_single_track_point(data_point)
        except Exception as ex:
            print(data_point)
            raise ex
        ret[fmt_date] = fmt_data

    return storm_code, ret


def process_storm_track_data(raw_data):
    """Processes storm track data from Weather Underground"""
    track_data = dict()
    for region, region_data in raw_data['storm_data'].items():
        for year, storms in region_data.items():
            for storm_id, storm_track_data in storms.items():
                t_id, t_data = __process_storm_track_data_points(region, year, storm_id,
                                                                 storm_track_data)
                track_data[t_id] = t_data

    return track_data


# - NASA Processing Functions

def __process_nasa_data(name, file):
    """Helper function to process NASA data"""
    if name == 'nasa_carbon_dioxide_levels':
        ret = __process_nasa_co2_data(file)
    elif name == 'nasa_sea_level':
        ret = __process_nasa_sea_level_data(file)
    elif name == 'nasa_temperature_anomaly':
        ret = __process_nasa_temp_data(file)
    else:
        ret = None

    return ret


def __process_nasa_co2_data(file):
    """Processes NASA CO2 Data"""
    with open(file, 'r') as fin:
        all_lines = fin.readlines()

    header_lines = np.array([1 for x in all_lines if x.startswith('#')]).sum()

    co2_data = pd.read_csv(file, skiprows=header_lines, header=None,
                           delim_whitespace=True)
    co2_data[co2_data == -99.99] = np.nan

    co2_data.columns = ['Year', 'Month', 'Year Fraction', 'Average', 'Interpolated',
                        'Trend', 'N Days']

    co2_data.set_index(['Year', 'Month'], inplace=True)
    new_idx = [datetime(x[0], x[1], 1) for x in co2_data.index]
    co2_data.index = new_idx
    co2_data.index.name = 'Date'

    return co2_data


def __process_nasa_sea_level_data(file):
    """Processes NASA Sea Level Change data"""
    with open(file, 'r') as fin:
        all_lines = fin.readlines()

    header_lines = np.array([1 for x in all_lines if x.startswith('HDR')]).sum()
    sea_level_data = pd.read_csv(file, delim_whitespace=True,
                                 skiprows=header_lines-1).reset_index()

    sea_level_data.columns = ['Altimeter Type', 'File Cycle', 'Year Fraction',
                              'N Observations', 'N Weighted Observations', 'GMSL',
                              'Std GMSL', 'GMSL (smoothed)', 'GMSL (GIA Applied)',
                              'Std GMSL (GIA Applied)', 'GMSL (GIA, smoothed)',
                              'GMSL (GIA, smoothed, filtered)']
    sea_level_data.set_index('Year Fraction', inplace=True)

    return sea_level_data


def __process_nasa_temp_data(file):
    """Processes NASA Temperature Anomaly data"""
    temp_data = pd.read_csv(file, sep='\t', header=None)
    temp_data.columns = ['Year', 'Annual Mean', 'Lowness Smoothing']
    temp_data.set_index('Year', inplace=True)

    return temp_data


def process_nasa_sea_surface_data(name, file):
    """Processes NASA Sea Surface Temperature data"""
    dt = datetime.strptime(name[-8:], '%Y%m%d')
    temp_data = pd.read_csv(file, sep=',', header=None)
    temp_data = temp_data.where(temp_data != 99999.0)

    temp_data.index = list(range(-90, 90))
    temp_data.index.name = 'Longitude'
    temp_data.columns = list(range(-180, 180))
    temp_data.columns.name = 'Latitude'

    return dt, temp_data


#
#   Script Functions
#

@click.group()
@click.pass_context
def cli(ctx):
    """Functions for processing the raw data"""
    ctx.ensure_object(dict)


@cli.command()
@click.pass_context
@click.option('--regions/--no-regions', default=True,
              help='Whether or not to process raw region data')
@click.option('--years/--no-years', default=True,
              help='Whether or not to process raw year-level storm data')
@click.option('--storms/--no-storms', default=True,
              help='Whether or not to process individual storm track data')
def wunderground(ctx, regions, years, storms):
    """Command to process the raw Weather Underground data"""
    raw_data = get_raw_wunderground_data(raw_data_dir)

    if regions:
        print('Processing region data... ', end='', flush=True)
        region_df = process_region_data(raw_data)

        with open(os.path.join(proc_data_dir, 'region_data.pkl'), 'wb') as fout:
            pickle.dump(region_df, fout)
        print('DONE')

    if years:
        print('Processing region-yearly data... ', end='', flush=True)
        region_year_df = process_region_yearly_data(raw_data)

        with open(os.path.join(proc_data_dir, 'region_yearly_data.pkl'), 'wb') as fout:
            pickle.dump(region_year_df, fout)
        print('DONE')

    if storms:
        print('Processing storm track data... ', end='', flush=True)
        storm_track_dict = process_storm_track_data(raw_data)

        with open(os.path.join(proc_data_dir, 'storm_track_data.pkl'), 'wb') as fout:
            pickle.dump(storm_track_dict, fout)
        print('DONE')


@cli.command()
@click.pass_context
def nasa(ctx):
    """Command to process raw NASA data"""
    # - Global Data
    fnames = __get_file_names_helper(raw_data_dir, 'txt')
    for k, v in fnames.items():
        print('Processing NASA data: {}... '.format(k), end='', flush=True)

        output = __process_nasa_data(k, v)
        if output is None:
            print('ERROR')
            continue

        with open(os.path.join(proc_data_dir, k + ".pkl"), 'wb') as fout:
            pickle.dump(output, fout)
        print('DONE')

    # - Sea surface temperature data
    print('Processing NASA sea surface data... ', end='', flush=True)

    fnames = __get_file_names_helper(raw_data_dir, 'csv')
    sea_surface_data = dict()
    for k, v in fnames.items():
        t_dt, t_data = process_nasa_sea_surface_data(k, v)
        sea_surface_data[t_dt] = t_data

    with open(os.path.join(proc_data_dir, 'sea_surface_temps.pkl'), 'wb') as fout:
        pickle.dump(sea_surface_data, fout)

    print('DONE')



#
#   Script Entry-Point
#

if __name__ == '__main__':
    cli(obj={})


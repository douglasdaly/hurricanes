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


#
#   Functions
#

def get_raw_data(raw_dir):
    """Loads the raw data"""
    fnames = dict([(x.split('.')[0], os.path.join(raw_data_dir, x))
               for x in os.listdir(raw_data_dir) if x.endswith('.pkl')])

    raw_data = dict()
    for k, v in fnames.items():
        with open(v, 'rb') as fin:
            raw_data[k] = pickle.load(fin)

    return raw_data


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
    raw_data = get_raw_data(raw_data_dir)

    if regions:
        print('Processing region data... ', end='', flush=True)
        region_df = process_region_data(raw_data)

        with open('data/processed/region_data.pkl', 'wb') as fout:
            pickle.dump(region_df, fout)
        print('DONE')

    if years:
        print('Processing region-yearly data... ', end='', flush=True)
        region_year_df = process_region_yearly_data(raw_data)

        with open('data/processed/region_yearly_data.pkl', 'wb') as fout:
            pickle.dump(region_year_df, fout)
        print('DONE')

    if storms:
        print('Processing storm track data... ', end='', flush=True)
        storm_track_dict = process_storm_track_data(raw_data)

        with open('data/processed/storm_track_data.pkl', 'wb') as fout:
            pickle.dump(storm_track_dict, fout)
        print('DONE')


#
#   Script Entry-Point
#

if __name__ == '__main__':
    cli(obj={})


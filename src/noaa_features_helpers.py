#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
noaa_features_helpers.py

    Helper functions to further process NOAA temperature data

@author: Douglas Daly
@date: 11/21/2018
"""
#
#   Imports
#
import os
import pickle
import calendar
from datetime import datetime, timedelta
import multiprocessing
import psutil

import numpy as np
import pandas as pd
from scipy import interpolate as interp

from tqdm import tqdm


#
#   Functions
#

def __load_noaa_processed_data(directory):
    """Helper to load the processed NOAA data"""
    with open(os.path.join(directory, 'ratpac_stations.pkl'), 'rb') as fin:
        station_data = pickle.load(fin)

    with open(os.path.join(directory, 'ratpac_b.pkl'), 'rb') as fin:
        ratpac_data = pickle.load(fin)

    # - Merge to add location data and dates
    all_data = ratpac_data.join(station_data.loc[:, ['LAT', 'LON']], on='station_number')

    dt_data = np.empty((all_data.shape[0], 1), dtype=datetime)
    for row_id, row_vals in enumerate(all_data.values):
        dt_data[row_id] = datetime(row_vals[1], row_vals[2],
                                   calendar.monthrange(row_vals[1], row_vals[2])[1])
    all_data['Date'] = dt_data

    all_data.drop(['year', 'month', 'station_number', 'station_id'], axis=1, inplace=True)

    return all_data


def __get_relevant_data(all_noaa_data, pressure_levels, out_name, start_year):
    """Helper to get relevant pressure level data"""
    cut_data = all_noaa_data.loc[:, ['Date', 'LON', 'LAT', 'surface'] + pressure_levels].copy()
    cut_data = cut_data.loc[cut_data.loc[:, 'Date'] >= datetime(start_year, 1, 1)]

    altitude_weights = np.log([float(x[:-2]) for x in pressure_levels]).reshape(1, len(pressure_levels))

    all_alt_weights = pd.DataFrame(np.repeat(altitude_weights, cut_data.shape[0], 0),
                                   index=cut_data.index, columns=pressure_levels)
    all_alt_weights = all_alt_weights.where(~cut_data.loc[:, pressure_levels].isnull())
    all_alt_weights = all_alt_weights.div(all_alt_weights.sum(axis=1), axis=0)

    cut_data[out_name] = cut_data.loc[:, pressure_levels].multiply(all_alt_weights).sum(axis=1)
    cut_data.drop(pressure_levels, axis=1, inplace=True)

    # - Need to reshape the data to make it easier to work with
    positions = list(zip(cut_data.loc[:, 'LON'].astype(float),
                         cut_data.loc[:, 'LAT'].astype(float)))
    cut_data['Position'] = positions

    cut_data.drop(['LON', 'LAT'], axis=1, inplace=True)
    cut_data.set_index(['Date', 'Position'], inplace=True)

    return cut_data


def __get_point_data_for_interpolation(noaa_data):
    """Helper to get point and value data for doing interpolation calculations"""
    unq_dates = np.sort(np.unique(noaa_data.index.get_level_values('Date')))

    orig_point_data = dict()
    interp_point_data = dict()
    for nm in noaa_data.columns:
        orig_point_data[nm] = list()
        interp_point_data[nm] = list()

        for i_dt in range(len(unq_dates)):
            dt = unq_dates[i_dt]
            t_values = noaa_data.loc[dt, nm]

            r_lons, r_lats = zip(*t_values.index.values)
            r_lons = np.array(r_lons)
            r_lats = np.array(r_lats)

            t_points = np.concatenate([r_lons.reshape(-1, 1), r_lats.reshape(-1, 1)], axis=1)
            t_values = t_values.values
            t_points = t_points[~np.isnan(t_values)]
            t_values = t_values[~np.isnan(t_values)]

            if len(t_values) <= 0:
                continue

            orig_point_data[nm].append((unq_dates[i_dt], t_points, t_values))

            # - Tesselate for boundary wrap (probably a better way to do this)
            t_nrmpts = t_points.copy()
            t_nrmpts[:, 0] += 180
            t_nrmpts[:, 1] += 90

            quad_pts = list()
            quad_vls = list()
            for i_x in range(3):
                for i_y in range(3):
                    t_qpts = t_nrmpts.copy()
                    t_qpts[:, 0] += 360 * i_x
                    t_qpts[:, 1] += 180 * i_y

                    quad_pts.append(t_qpts)
                    quad_vls.append(t_values.copy())

            quad_pts = np.concatenate(quad_pts, axis=0)
            quad_vls = np.concatenate(quad_vls, axis=0)

            quad_pts[:, 0] -= (360 + 180)
            quad_pts[:, 1] -= (180 + 90)

            qpt_mask = (quad_pts[:, 0] >= -360) & (quad_pts[:, 0] <= 360) \
                       & (quad_pts[:, 1] >= -180) & (quad_pts[:, 1] <= 180)

            quad_pts = quad_pts[qpt_mask]
            quad_vls = quad_vls[qpt_mask]
            interp_point_data[nm].append((unq_dates[i_dt], quad_pts, quad_vls))

    return orig_point_data, interp_point_data


def __map_wrap_do_interpolation_single_point(args):
    """Pool mapper wrapper for __do_interpolation_single_point function"""
    return args[0], __do_interpolation_single_point(*args[1:])


def __do_interpolation_single_point(points, values, method):
    """Interpolates a single set of points"""
    gx, gy = np.mgrid[-360:360, -180:180]
    rbfi = interp.Rbf(points[:, 0], points[:, 1], values, function=method)
    t_result = rbfi(gx, gy)
    return t_result[180:(180+360), 90:(90+180)]


def __do_interpolation_multi_thread(point_data, method, show_progress, max_processes=None,
                                    chunk_size=1):
    """Does interpolation calculations in a multi-threaded fashion"""
    if max_processes is None:
        max_processes = psutil.cpu_count(logical=False)

    if max_processes == 1:
        return __do_interpolation_single_thread(point_data, method, show_progress)

    status_str = "Interpolating {} data"

    interp_results = dict()
    for nm, t_intrp_data in point_data.items():
        if not show_progress:
            print(status_str.format(nm) + "... ", end='', flush=True)
            with multiprocessing.Pool(max_processes) as p:
                interp_results[nm] = dict(p.imap_unordered(__map_wrap_do_interpolation_single_point,
                                                           [(*x, method) for x in t_intrp_data],
                                                           chunk_size))
            print('DONE')
        else:
            with multiprocessing.Pool(max_processes) as p:
                interp_results[nm] = dict(tqdm(p.imap_unordered(__map_wrap_do_interpolation_single_point,
                                                                [(*x, method) for x in t_intrp_data],
                                                                chunk_size),
                                               desc=status_str.format(nm), total=len(t_intrp_data),
                                               leave=False))
            print('\r' + status_str.format(nm) + '... DONE', flush=True)

    return interp_results


def __do_interpolation_single_thread(point_data, method, show_progress):
    """Does interpolation calculations on the given point data"""
    interp_results = dict()
    for nm, t_intrp_data in point_data.items():
        interp_results[nm] = dict()

        status_str = 'Interpolating {} data'.format(nm)

        to_iter = range(len(t_intrp_data))
        if show_progress:
            to_iter = tqdm(to_iter, leave=False, desc=status_str)
        else:
            print(status_str + '... ', end='', flush=True)

        for i_dt in to_iter:
            t_dt, intrp_pts, intrp_vals = t_intrp_data[i_dt]
            t_result = __do_interpolation_single_point(intrp_pts, intrp_vals, method)
            interp_results[nm][t_dt] = t_result

        done_str = 'DONE'
        if show_progress:
            done_str = '\r{}... '.format(status_str) + done_str

        print(done_str, flush=True)

    return interp_results


#
#   Main Helpers
#

def generate_noaa_interpolation_data(data_dir, pressure_levels, out_name='aloft',
                                     start_year=1965, method='multiquadric', show_progress=True,
                                     multi_thread=True, max_processes=None, chunk_size=1):
    """Function to generate interpolations for NOAA temperature data"""
    print('Loading processed data... ', end='', flush=True)
    proc_data = __load_noaa_processed_data(data_dir)
    print('DONE')

    print('Extracting and averaging desired altitude data... ', end='', flush=True)
    cut_data = __get_relevant_data(proc_data, pressure_levels, out_name, start_year)
    print('DONE')

    print('Converting to point data for interpolation... ', end='', flush=True)
    orig_pt_data, interp_pt_data = __get_point_data_for_interpolation(cut_data)
    print('DONE')

    # - Do the interpolation
    output_orig_data = dict()
    for nm in orig_pt_data.keys():
        output_orig_data[nm] = dict([(x[0], (x[1], x[2])) for x in orig_pt_data[nm]])

    if multi_thread:
        interp_results = __do_interpolation_multi_thread(interp_pt_data, method, show_progress,
                                                         max_processes, chunk_size)
    else:
        interp_results = __do_interpolation_single_thread(interp_pt_data, method, show_progress)

    # - Generate difference data set
    print('Generating difference set... ', end='', flush=True)
    output_orig_data['diff'] = output_orig_data['surface'].copy()
    for k, v in output_orig_data['diff'].items():
        t_out = v[1].copy()
        t_sub_k = output_orig_data[out_name][k][0]
        t_sub_v = output_orig_data[out_name][k][1]
        for pos_tup in v[0]:
            t_out[(v[0] == pos_tup).all(axis=1)] -= t_sub_v[(t_sub_k == pos_tup).all(axis=1)]
        output_orig_data['diff'][k] = (v[0], t_out)

    interp_results['diff'] = interp_results['surface'].copy()
    for k in interp_results['diff'].keys():
        interp_results['diff'][k] -= interp_results[out_name][k]
    print('DONE')

    return output_orig_data, interp_results

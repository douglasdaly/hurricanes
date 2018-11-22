#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_features.py

    Script to process data further into features

@author: Douglas Daly
@date: 11/21/2018
"""
#
#   Imports
#
import os
import pickle
import click

from noaa_features_helpers import generate_noaa_interpolation_data


#
#   Script Functions
#

@click.group()
@click.pass_context
def cli(ctx):
    """Functions for generating feature data"""
    ctx.ensure_object(dict)


@cli.group()
@click.pass_context
def noaa(ctx):
    """Functions for operating on NOAA data"""
    ctx.ensure_object(dict)


@noaa.command()
@click.pass_context
@click.option('--input_dir', default='data/processed', type=str, help='Processed data dir for input data')
@click.option('--output_dir', default='data/features', type=str, help='Output dir for generated data')
@click.option('--pressure-levels', default='200,150,100,70', type=str, help='Pressure levels to average')
@click.option('--out-name', default='aloft', type=str, help='Combined pressure levels name')
@click.option('--start-year', default=1965, type=int, help='Starting year to cut data to')
@click.option('--method', default='multiquadric', type=str, help='RBF function method to use')
@click.option('--progress/--no-progress', default=True, help='Show progress bar during calculations')
@click.option('--multi-thread/--single-thread', default=True, help='Do calculations with multi-threading')
@click.option('--max-processes', default=None, type=int, help='Max processes to run multi-threaded')
@click.option('--chunk-size', default=1, type=int, help='Chunk size for multi-processing')
def interpolate(ctx, input_dir, output_dir, pressure_levels, out_name, start_year,
                method, progress, multi_thread, max_processes, chunk_size):
    """Generates interpolation data for NOAA temperatures"""
    # - Arg handling
    progress = True
    p_levels = [x.lower() if x.lower().endswith('mb') else x.lower()+'mb'
                for x in pressure_levels.split(',')]

    # - Do calculation
    orig_pt_data, interpolated_data = generate_noaa_interpolation_data(input_dir, p_levels,
                                          out_name, start_year, method, progress, multi_thread,
                                          max_processes, chunk_size)

    # - Save output
    print('Saving original point data output... ', end='', flush=True)
    with open(os.path.join(output_dir, 'noaa_orig_point_data.pkl'), 'wb') as fout:
        pickle.dump(orig_pt_data, fout)
    print('DONE')

    print('Saving interpolation output data... ', end='', flush=True)
    with open(os.path.join(output_dir, 'noaa_interpolated_point_data.pkl'), 'wb') as fout:
        pickle.dump(interpolated_data, fout)
    print('DONE')


#
#   Script Entry-point
#

if __name__ == "__main__":
    cli(obj={})

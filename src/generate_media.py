#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_media.py

    Script for media generating functions

@author: Douglas Daly
@date: 11/23/2018
"""
#
#   Imports
#
import os
import pickle
import shutil
import tempfile
import subprocess
from datetime import datetime
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import cartopy.crs as ccrs
import moviepy.editor as mpy
from PIL import Image
from io import BytesIO

import papermill as pm

from tqdm import tqdm
import click


#
#   Helper Functions
#

def __heatmap_plot_data(data, zorder=None, color=None, marker=None, color_map=None,
                        alpha=1, label=None, interpolation='none', origin='lower',
                        extent=[-180, 180, -90, 90], vmin=None, vmax=None, ax=None):
    """Helper to plot heatmap data"""
    if ax is None:
        ax = plt.gca()

    if type(data) == np.ndarray or type(data) == np.array:
        if len(data.shape) == 1:
            # - 1D Data
            raise NotImplementedError('Data type not currently supported')
        elif len(data.shape) == 2:
            # - 2D Data
            if data.shape[1] == 2:
                # -- (x, y) data
                axr = ax.scatter(data[:, 0], data[:, 1], marker=marker, color=color,
                                 alpha=alpha, zorder=zorder, label=label)
            elif data.shape[1] > 2:
                # -- Heatmap data
                axr = ax.imshow(data.T, extent=extent, interpolation=interpolation,
                                cmap=color_map, origin=origin, alpha=alpha, zorder=zorder,
                                vmin=vmin, vmax=vmax)
            else:
                raise NotImplementedError('Data type not currently supported')
        else:
            # -- Unknown
            raise NotImplementedError('Data type not currently supported')
    else:
        # - Not supported
        raise NotImplementedError('Data type not currently supported')

    return axr


def __heatmap_draw_plots(li_plt, ax, markers=['x', '.', 'o'], colors=['b', 'r', 'g'],
                         color_map=None, center=None, vmin=None, vmax=None,
                         show_colorbar=False, colorbar_label=None):
    """Helper function to draw the given plots"""
    i_z = 2
    i_m = 0
    i_c = 0

    axr = list()
    for i_pd in range(len(li_plt)):
        plt_dat = li_plt[i_pd]
        if isinstance(plt_dat, np.ndarray):
            plt_normed = plt_dat.copy()
            if center is not None:
                if vmin is None:
                    vmin = plt_dat.min()
                if vmax is None:
                    vmax = plt_dat.max()

                if np.abs(vmin) < np.abs(vmax):
                    vmin = np.abs(vmax) * np.sign(vmin)
                else:
                    vmax = np.abs(vmin) * np.sign(vmax)

                plt_normed[plt_dat < center] = np.maximum(plt_dat[plt_dat < center] / vmin, -1) * vmin
                plt_normed[plt_dat >= center] = np.minimum(plt_dat[plt_dat >= center]/ np.abs(vmax), 1) * vmax

            t_axr = __heatmap_plot_data(plt_normed, zorder=i_z, color_map=color_map, alpha=0.5,
                                        vmin=vmin, vmax=vmax, ax=ax)
            if show_colorbar:
                cbar = plt.colorbar(t_axr, shrink=0.8)
                if colorbar_label is not None:
                    cbar.set_label(colorbar_label)

            axr.append(t_axr)
        else:
            axr.append(__heatmap_plot_data(plt_dat[0], zorder=i_z, color=colors[i_c], marker=markers[i_m],
                                           ax=ax))
            i_m = (i_m + 1) % len(markers)
            i_c = (i_c + 1) % len(colors)
        i_z += 1

    return axr


def __index_helper(to_search, index):
    """Helper function to get correct index for to_search array"""
    try:
        # - See if we got an integer input
        idx = int(index)
        # -- Year or index number?
        if idx > len(to_search):
            if type(to_search[0]) == np.datetime64:
                idx = np.array([pd.to_datetime(x).year == idx for x in to_search]).astype(int).argmax()
            else:
                idx = idx % len(to_search)
    except Exception:
        # - Otherwise do any additional conversions
        if type(to_search[0]) == np.datetime64:
            index = pd.to_datetime(index)
        idx = np.array([pd.to_datetime(x) == index for x in to_search]).astype(int).argmax()

    return idx


#
#   Script Functions
#

@click.group()
@click.pass_context
def cli(ctx):
    """Functions for generating various media files"""
    ctx.ensure_object(dict)


# - Jupyter Notebooks through Papermill

@cli.command()
@click.pass_context
@click.argument('notebook_file', type=str)
@click.option('--output-file', type=str, default=None, help='Where to save the output notebook')
@click.option('--parameter', '-p', nargs=2, type=click.Tuple([str, str]), multiple=True,
              help='Additional papermill parameters to pass')
def notebook(ctx, notebook_file, output_file, parameter):
    """Run a jupyter notebook through the papermill utility"""
    # - Arg handling
    if output_file is None:
        file_name = notebook_file.split('/')[-1].split('.')[0]
        output_file = 'logs/generate_media/{}-output.ipynb'.format(file_name)

    # - Validity checks
    if not os.path.isfile(notebook_file):
        print('ERROR: Input file does not exist')
        return

    if not notebook_file.endswith('ipynb'):
        print('ERROR: Invalid input file given (must be .ipynb)')
        return

    # - Process parameters
    print('Processing parameters... ', end='', flush=True)
    param_dict = dict()

    # -- Tack on standard parameters
    param_dict['raw_data_dir'] = 'data/raw'
    param_dict['processed_data_dir'] = 'data/processed'
    param_dict['feature_data_dir'] = 'data/features'
    param_dict['media_dir'] = 'media/'

    for (k, v) in parameter:
        param_dict[k] = v
    print('DONE')

    # - Run it
    pm.execute_notebook(
        notebook_file,
        output_file,
        parameters = param_dict
    )


# - Heatmaps

@cli.group()
@click.pass_context
@click.option('--figsize-width', type=float, default=12, help='Width for the figures')
@click.option('--figsize-height', type=float, default=8, help='Height for the figures')
@click.option('--color-map', type=str, default='coolwarm', help='Colormap to use')
@click.option('--dpi', type=int, default=None, help='DPI to use for output images')
def heatmap(ctx, figsize_width, figsize_height, color_map, dpi):
    """Functions for generating heatmap media"""
    ctx.obj['figsize_width'] = figsize_width
    ctx.obj['figsize_height'] = figsize_height
    ctx.obj['color_map'] = color_map
    ctx.obj['dpi'] = dpi


@heatmap.command()
@click.pass_context
@click.argument('input_files', type=str)
@click.option('--output', type=str, default=None, help='Output file to save media as')
@click.option('--smooth', type=int, default=None, help='Average this number of data points together')
@click.option('--show-colorbar', is_flag=True, default=False, help='Append the colorbar scale to the plot')
@click.option('--colorbar-label', type=str, default=None, help='Label for the displayed color bar')
@click.option('--percentile', type=int, default=5, help='Percentile to use for min/max values')
@click.option('--title', type=str, default=None, help='Figure title to use')
@click.option('--index', type=str, default=None, help='Index to use from input data')
@click.option('--end-index', type=str, default=None, help='Ending index to use from input data')
@click.option('--animate', is_flag=True, default=False, help='Create animation for output')
@click.option('--fps', type=int, default=12, help='FPS to use in animation')
@click.option('--compress', is_flag=True, default=False, help='Compress output files')
@click.option('--use-optimage', is_flag=True, default=False, help='Use optimage tool to further compress files')
def globe(ctx, input_files, output, smooth, show_colorbar, colorbar_label, percentile,
          title, index, end_index, animate, fps, compress, use_optimage):
    """Generates heatmaps plotted with global coastlines in the background"""
    # - Context/arg handling
    fig_sz = (ctx.obj.get('figsize_width', None), ctx.obj.get('figsize_height', None))
    if fig_sz[0] is None and fig_sz[1] is None:
        fig_sz = None
    cm = ctx.obj.get('color_map', None)

    dpi = ctx.obj.get('dpi', None)
    if dpi is None:
        dpi = plt.rcParams['savefig.dpi']

    if output is None:
        compress = False
    else:
        if animate:
            if output.lower().endswith('.mp4'):
                output_gif = False
            elif output.lower().endswith('gif'):
                output_gif = True
            else:
                print('Invalid output file type specified for animation: {}'.format(output.split('.')[-1]))
                return

    # - Load data
    print('Loading and formatting input data... ', end='', flush=True)
    input_data = list()
    for fn in input_files.split(','):
        if not os.path.isfile(fn):
            print('Invalid input file given: {}'.format(fn))
            return
        with open(fn, 'rb') as fin:
            input_data.append(pickle.load(fin))

    # - Get input_data index data type (if needed)
    input_idx_type = type(next(iter(input_data[0])))

    # - Get data to plot
    vmin = None
    vmax = None
    to_plot = list()
    idx_names = list()
    all_idxs = set()
    for inp_dat in input_data:
        if type(inp_dat) == dict:
            all_idxs = all_idxs.union(inp_dat.keys())

    all_idxs = list(all_idxs)
    all_idxs.sort()
    for t_idx in all_idxs:
        t_list = list()
        for inp_dat in input_data:
            if t_idx in inp_dat.keys():
                t_list.append(inp_dat[t_idx])
                if isinstance(inp_dat[t_idx], np.ndarray):
                    if vmin is None:
                        vmin = list()
                        vmax = list()
                    vmin.append(inp_dat[t_idx].min())
                    vmax.append(inp_dat[t_idx].max())
        idx_names.append(t_idx)
        to_plot.append(t_list)

    vmin = np.array(vmin)
    vmax = np.array(vmax)

    print('DONE')

    # - Smoothing
    if smooth is not None:
        vmin = list()
        vmax = list()
        smooth_plot = list()
        smooth_names = list()
        smooth_idxs = list(range(0, len(to_plot), smooth))
        for i in range(len(smooth_idxs)):
            sm_st_idx = smooth_idxs[i]

            tmp_to_add = list()
            tmp_divisor = 0.0
            for j in range(smooth):
                full_idx = sm_st_idx + j
                if full_idx >= len(to_plot):
                    continue

                tmp_divisor += 1.0
                tmp_liplt = to_plot[full_idx]
                for k in range(len(tmp_liplt)):
                    tmp_plt = tmp_liplt[k]
                    if j == 0:
                        tmp_to_add.append(tmp_plt)
                    else:
                        if isinstance(tmp_plt, np.ndarray):
                            tmp_to_add[k] += tmp_plt

            for k in range(len(tmp_to_add)):
                tmp_to_adj = tmp_to_add[k]
                if isinstance(tmp_to_adj, np.ndarray):
                    tmp_to_add[k] /= tmp_divisor
                    vmin.append(tmp_to_add[k].min())
                    vmax.append(tmp_to_add[k].max())

            smooth_names.append(idx_names[sm_st_idx])
            smooth_plot.append(tmp_to_add)

        idx_names = smooth_names
        to_plot = smooth_plot
        vmin = np.array(vmin)
        vmax = np.array(vmax)

    if isinstance(vmin, np.ndarray):
        vmin = np.percentile(vmin, percentile)
        vmax = np.percentile(vmax, 100 - percentile)

    if index is not None:
        idx = __index_helper(idx_names, index)
    else:
        idx = 0

    if end_index is not None:
        end_idx = __index_helper(idx_names, end_index)
    else:
        end_idx = len(idx_names)

    if not animate:
        idx_names = [idx_names[idx]]
        to_plot = [to_plot[idx]]
    else:
        idx_names = idx_names[idx:end_idx]
        to_plot = to_plot[idx:end_idx]

    if len(to_plot) <= 1:
        animate = False
    elif len(to_plot) > 1 and not output:
        usr_inp = click.confirm('There are {} plots and no output specified, continue?'.format(len(to_plot)),
                                default=False)
        if usr_inp is False:
            return

    if animate:
        tmp_dir = tempfile.mkdtemp()

    if output is not None:
        plt.ioff()

    # - Generate plots
    out_list = list()
    iter_rng = range(len(to_plot))
    if len(to_plot) > 1:
        iter_rng = tqdm(iter_rng, desc='Generating individual plots', leave=False)
    else:
        print('Generating plot... ', end='', flush=True)

    for ix in iter_rng:
        li_plt = to_plot[ix]
        t_idx_nm = idx_names[ix]

        if input_idx_type == np.datetime64:
            t_idx_nm = pd.to_datetime(t_idx_nm).date().strftime('%Y')

        fig = plt.figure(figsize=fig_sz)
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

        ax.coastlines(zorder=0, alpha=1.0)

        ax.axhline(0, linestyle='-', linewidth=0.75, color='grey', zorder=1)
        ax.axvline(0, linestyle='-', linewidth=0.75, color='grey', zorder=1)

        ax.set_title('{}'.format(t_idx_nm))
        ax.set_xlabel('Longitude')
        ax.xaxis.set_visible(True)
        ax.set_ylabel('Latitude')
        ax.yaxis.set_visible(True)
        ax.grid(True, color='grey', linestyle='--', alpha=1, zorder=1)

        __heatmap_draw_plots(li_plt, ax, color_map=cm, center=0., vmin=vmin, vmax=vmax,
                             show_colorbar=show_colorbar, colorbar_label=colorbar_label)

        if title is not None:
            fig.suptitle(title)

        if output is not None:
            if animate:
                t_out = os.path.join(tmp_dir, '{}_'.format(ix) +
                                     ''.join(output.replace('/', '-').split('.')[:-1]) + ".png")
            else:
                t_out = output

            out_list.append(t_out)

            if compress:
                out_stream = BytesIO()
                fig.savefig(out_stream, dpi=dpi)
                out_stream.seek(0)
                im_in = Image.open(out_stream)
                im_out = im_in.convert('RGB').convert('P', palette=Image.ADAPTIVE)
                im_out.save(t_out)

                if use_optimage:
                    sp_ret = subprocess.run(['optimage', '--replace', t_out],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if sp_ret.returncode != 0:
                        err_str = sp_ret.stderr.decode('utf-8').strip()
                        use_optimage = False
                        if len(to_plot) > 1:
                            iter_rng.write('WARNING: Could not utilize optimage library')
                            iter_rng.write('  ' + err_str)
                        else:
                            print('WARNING')
                            print('  Could not utilize optimage library:')
                            print('    ', end='', flush=True)
                            print(err_str)
                            print('Generating plot... ', end='', flush=True)

            else:
                fig.savefig(t_out, dpi=dpi)

            plt.close(fig)

    if len(out_list) > 1:
        # - Create GIF/MP4
        print('\rGenerating individual plots... DONE', end='', flush=True)

        clip = mpy.ImageSequenceClip(out_list, fps=fps)

        if output_gif:
            if shutil.which('magick') is None and shutil.which('convert') is None:
                clip.write_gif(output, opt='nq')
            else:
                clip.write_gif(output, program='ImageMagick', opt='optimizeplus')
                print()
        else:
            clip.write_videofile(output, audio=False)

        print('Removing temporary files... ', end='', flush=True)
        shutil.rmtree(tmp_dir)
        print('DONE')
    else:
        print('DONE')
        if output is None:
            # - Show plot
            plt.show()


#
#   Script Entry-point
#

if __name__ == '__main__':
    cli(obj={})

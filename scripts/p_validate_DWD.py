#!/usr/bin/env python3

import sys
import os
import copy

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns

## ============================ ##

DATAPATH = './'
FIGUREPATH = './'

## ============================ ##

df = pd.read_csv(os.path.join(DATAPATH, 'municipality_shape_era5_dwd.csv'))
df2 = pd.read_csv(os.path.join(DATAPATH, 'data_gemeinde_2008-2023_air_temperature_daymean_invdistances_100km.csv'))
df = df.merge(df2, on='AGS', how='outer')

#df['era5_total_precipitation'] = df['era5_total_precipitation'] * (365.25 / 12.) * 1000
#df['dwd_precipitation'] = df['dwd_precipitation'] * 1000
#df['diff_temperature'] = df['era5_2m_temperature'] - df['dwd_air_temperature_mean']
#df['diff_precipitation'] = df['era5_total_precipitation'] - df['dwd_precipitation']

df['diff_temperature_dwd'] = df['dwd_air_temperature_mean'] - (df['TT_TU'] + 273.15)

## ============================ ##
"""
fig, ax = plt.subplots(figsize=(5, 4))
ax.hist(df['diff_temperature'], bins=np.arange(-4.5, 4.5+0.1, 0.1))
ylims = ax.get_ylim()
ax.plot([0., 0.], ylims, 'k-')
ax.set_ylim(ylims)
ax.set_ylabel('Municipalities')
ax.set_xlabel('Temperature at 2 metres (degree C)\nERA5 minus DWD grid')
sns.despine(ax=ax, offset=1., right=True, top=True)
#plt.xticks(rotation=10)
fig.savefig(os.path.join(FIGUREPATH, 'histogram_difference_temperature.pdf'), dpi=300, bbox_inches='tight', transparent=True)

fig, ax = plt.subplots(figsize=(5, 4))
ax.hist(df['diff_precipitation'], bins=np.arange(-50., 50+2, 2))
ylims = ax.get_ylim()
ax.plot([0., 0.], ylims, 'k-')
ax.set_ylim(ylims)
ax.set_ylabel('Municipalities')
ax.set_xlabel('Precipitation (mm month-1)\nERA5 minus DWD grid')
sns.despine(ax=ax, offset=1., right=True, top=True)
#plt.xticks(rotation=10)
fig.savefig(os.path.join(FIGUREPATH, 'histogram_difference_precipitation.pdf'), dpi=300, bbox_inches='tight', transparent=True)
"""
## ============================ ##

fig, ax = plt.subplots(figsize=(5, 4))
ax.hist(df['diff_temperature_dwd'], bins=np.arange(-4.5, 4.5+0.1, 0.1))
ylims = ax.get_ylim()
ax.plot([0., 0.], ylims, 'k-')
ax.set_ylim(ylims)
ax.set_ylabel('Municipalities')
ax.set_xlabel('Temperature at 2 metres (degree C)\nDWD grid minus DWD stations')
sns.despine(ax=ax, offset=1., right=True, top=True)
#plt.xticks(rotation=10)
fig.savefig(os.path.join(FIGUREPATH, 'histogram_difference_temperature_dwd.pdf'), dpi=300, bbox_inches='tight', transparent=True)

## ============================ ##
"""
import geopandas as gpd

datafile = "VG250_GEM.shp"
gdf_muni = gpd.read_file(os.path.join(DATAPATH, datafile)).to_crs('epsg:4326')
gdf_muni['AGS'] = gdf_muni['AGS'].astype(int)

datafile = "stations.shp"
gdf_stations = gpd.read_file(os.path.join(DATAPATH, datafile))

gdf = gdf_muni.merge(df, on='AGS', how='outer')

cmap = plt.cm.seismic
bounds = np.arange(-3., 3.5, 0.5)
norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
formatcode = '%.1f'

fig, ax = plt.subplots(figsize=(4,6))
ax2 = fig.add_axes([0.94, 0.16, 0.03, 0.68])
cb = mpl.colorbar.ColorbarBase(ax2, cmap=cmap, norm=norm,
				spacing='uniform', ticks=bounds, boundaries=bounds, format=formatcode,
				extend='both', orientation='vertical')
cb.ax.tick_params(labelsize='medium')
cb.set_label(label="Temperature at 2 metres (degree C)\n ERA5 minus DWD stations", size='medium')
gdf_muni.plot(ax=ax, alpha=1., facecolor='none', lw=0.5, edgecolor='k')
gdf.plot(ax=ax, alpha=1., column='diff', lw=0.2, cmap=cmap, norm=norm, edgecolor='none', markersize=1.)
gdf_stations.plot(ax=ax, markersize=1., marker='o', color='m')
#ax.set_xlim(-130., 180.)
#ax.set_ylim(-60., 75.)
ax.set_xlabel(None)
ax.set_ylabel(None)
ax.set_xticks([])
ax.set_yticks([])
fig.savefig(os.path.join(FIGUREPATH, 'map_difference.png'), bbox_inches='tight', dpi=400)
"""
## ============================ ##

import geopandas as gpd

datafile = "VG250_GEM.shp"
gdf_muni = gpd.read_file(os.path.join(DATAPATH, datafile)).to_crs('epsg:4326')
gdf_muni['AGS'] = gdf_muni['AGS'].astype(int)

datafile = "stations.shp"
gdf_stations = gpd.read_file(os.path.join(DATAPATH, datafile))

gdf = gdf_muni.merge(df, on='AGS', how='outer')

cmap = plt.cm.seismic
bounds = np.arange(-3., 3.5, 0.5)
norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
formatcode = '%.1f'

fig, ax = plt.subplots(figsize=(4,6))
ax2 = fig.add_axes([0.94, 0.16, 0.03, 0.68])
cb = mpl.colorbar.ColorbarBase(ax2, cmap=cmap, norm=norm,
				spacing='uniform', ticks=bounds, boundaries=bounds, format=formatcode,
				extend='both', orientation='vertical')
cb.ax.tick_params(labelsize='medium')
cb.set_label(label="Temperature at 2 metres (degree C)\nDWD grid minus DWD stations", size='medium')
gdf_muni.plot(ax=ax, alpha=1., facecolor='none', lw=0.5, edgecolor='k')
gdf.plot(ax=ax, alpha=1., column='diff_temperature_dwd', lw=0.2, cmap=cmap, norm=norm, edgecolor='none', markersize=1.)
gdf_stations.plot(ax=ax, markersize=1., marker='o', color='m')
#ax.set_xlim(-130., 180.)
#ax.set_ylim(-60., 75.)
ax.set_xlabel(None)
ax.set_ylabel(None)
ax.set_xticks([])
ax.set_yticks([])
fig.savefig(os.path.join(FIGUREPATH, 'map_difference_DWD.png'), bbox_inches='tight', dpi=400)

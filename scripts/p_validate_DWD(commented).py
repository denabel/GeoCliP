#!/usr/bin/env python3

## ============================================================= ##
## PACKAGE INSTALLATION
## ============================================================= ##
## Before running this script, make sure all required packages are
## installed in your Python environment. You can install them via pip:
##
##   pip install numpy pandas matplotlib seaborn geopandas
##
## Or if you are using a conda environment (recommended for geopandas,
## which has complex geospatial dependencies):
##
##   conda install numpy pandas matplotlib seaborn
##   conda install -c conda-forge geopandas
##
## Package versions this script was developed with (for reference):
##   Python     >= 3.8
##   numpy      >= 1.21
##   pandas     >= 1.3
##   matplotlib >= 3.4
##   seaborn    >= 0.11
##   geopandas  >= 0.10
##
## To check your currently installed versions, run:
##   pip show numpy pandas matplotlib seaborn geopandas
## ============================================================= ##

## ============================================================= ##
## STANDARD LIBRARY IMPORTS (no installation needed)
## ============================================================= ##
import sys    # System-specific parameters and functions (e.g. sys.exit, sys.argv)
import os     # File path handling (os.path.join, os.path.exists, etc.)
import copy   # Deep/shallow copying of objects

## ============================================================= ##
## THIRD-PARTY IMPORTS (require installation, see above)
## ============================================================= ##

# numpy: fundamental package for numerical computing in Python.
# Used here for array operations and bin edge construction (np.arange).
import numpy as np

# pandas: core library for tabular data manipulation.
# Used for loading CSVs and merging datasets on the AGS district key.
import pandas as pd

# matplotlib: the base plotting library. pyplot provides a MATLAB-like
# interface for creating figures and axes. mpl (the top-level module)
# is imported separately to access lower-level objects like
# BoundaryNorm and ColorbarBase used in the choropleth map.
import matplotlib.pyplot as plt
import matplotlib as mpl

# seaborn: statistical visualisation library built on top of matplotlib.
# Used here mainly for despine() to clean up axis borders on plots.
import seaborn as sns

## ============================================================= ##
## CONFIGURATION
## ============================================================= ##
# Base directory where input data files are located.
# './' means the current working directory (i.e. the folder you run
# the script from). Change these if your data/figures live elsewhere,
# e.g. DATAPATH = '/home/user/projects/climate/data/'
DATAPATH = './'

# Directory where output figures will be saved.
FIGUREPATH = './'

## ============================================================= ##
## DATA LOADING AND MERGING
## ============================================================= ##
# Load the municipality-level shape/ERA5/DWD metadata table.
# This file contains spatial and climate attributes per municipality,
# indexed by the AGS (Amtlicher Gemeindeschlüssel) district code.
df = pd.read_csv(os.path.join(DATAPATH, 'municipality_shape_era5_dwd.csv'))

# Load the DWD (Deutscher Wetterdienst) daily mean air temperature data
# interpolated to municipality level using inverse distance weighting
# with a 100 km radius, covering 2008–2023.
df2 = pd.read_csv(os.path.join(DATAPATH, 'data_gemeinde_2008-2023_air_temperature_daymean_invdistances_100km.csv'))

# Merge both tables on the AGS key using an outer join so that
# all municipalities from either source are retained.
df = df.merge(df2, on='AGS', how='outer')

## ============================================================= ##
## COMMENTED-OUT ALTERNATIVE DIFFERENCE CALCULATIONS
## ============================================================= ##
# The lines below were used in an earlier version of the script to
# compute ERA5-vs-DWD differences for temperature and precipitation.
# They are kept for reference but are currently inactive.
#
#   era5_total_precipitation * (365.25/12.) * 1000 converts from
#   m/s (ERA5 native units) to mm/month.
#   diff_temperature = ERA5 2m temperature minus DWD mean temperature
#   diff_precipitation = ERA5 precipitation minus DWD precipitation

#df['era5_total_precipitation'] = df['era5_total_precipitation'] * (365.25 / 12.) * 1000
#df['dwd_precipitation'] = df['dwd_precipitation'] * 1000
#df['diff_temperature'] = df['era5_2m_temperature'] - df['dwd_air_temperature_mean']
#df['diff_precipitation'] = df['era5_total_precipitation'] - df['dwd_precipitation']

## ============================================================= ##
## FEATURE ENGINEERING: TEMPERATURE DIFFERENCE
## ============================================================= ##
# Compute the difference between the DWD gridded temperature product
# and the DWD station-based temperature.
# Note: TT_TU is in degrees Celsius, while dwd_air_temperature_mean
# is in Kelvin — adding 273.15 converts TT_TU to Kelvin before
# subtracting, so the result is in degrees Celsius.
df['diff_temperature_dwd'] = df['dwd_air_temperature_mean'] - (df['TT_TU'] + 273.15)

## ============================================================= ##
## COMMENTED-OUT FIGURES: ERA5 VS DWD HISTOGRAMS
## ============================================================= ##
# The triple-quoted block below contains histogram plots comparing
# ERA5 reanalysis data against DWD gridded data for both temperature
# and precipitation. These were produced in an earlier analysis stage
# and are preserved for reference but not currently executed.
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

## ============================================================= ##
## FIGURE 1: HISTOGRAM OF TEMPERATURE DIFFERENCE (DWD GRID VS STATIONS)
## ============================================================= ##
# Plots the distribution of the per-municipality temperature difference
# (DWD gridded product minus DWD station observations) across all municipalities.
# The vertical black line at x=0 marks zero difference as a visual reference.
# Bin width is 0.1°C, ranging from -4.5°C to +4.5°C.
# transparent=True makes the figure background transparent for use in publications.
fig, ax = plt.subplots(figsize=(5, 4))
ax.hist(df['diff_temperature_dwd'], bins=np.arange(-4.5, 4.5+0.1, 0.1))
ylims = ax.get_ylim()
ax.plot([0., 0.], ylims, 'k-')   # Vertical reference line at zero difference
ax.set_ylim(ylims)
ax.set_ylabel('Municipalities')
ax.set_xlabel('Temperature at 2 metres (degree C)\nDWD grid minus DWD stations')
sns.despine(ax=ax, offset=1., right=True, top=True)
#plt.xticks(rotation=10)
fig.savefig(os.path.join(FIGUREPATH, 'histogram_difference_temperature_dwd.pdf'), dpi=300, bbox_inches='tight', transparent=True)

## ============================================================= ##
## COMMENTED-OUT FIGURE: MAP OF ERA5 VS DWD TEMPERATURE DIFFERENCE
## ============================================================= ##
# The triple-quoted block below is an earlier version of the choropleth
# map that compared ERA5 reanalysis against DWD station data (column='diff').
# It is superseded by the active map below which uses the DWD-grid-vs-stations
# difference instead (column='diff_temperature_dwd').
# Kept for reference in case the ERA5 comparison is needed again.
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

## ============================================================= ##
## FIGURE 2: CHOROPLETH MAP OF TEMPERATURE DIFFERENCE (DWD GRID VS STATIONS)
## ============================================================= ##

# geopandas is imported here rather than at the top of the script
# because it is only needed for the map figures.
import geopandas as gpd

# Load the VG250 German municipality boundary shapefile and reproject
# to WGS84 (EPSG:4326) so coordinates are in degrees latitude/longitude.
# VG250 is the 1:250,000 scale version — higher resolution than VG5000.
datafile = "VG250_GEM.shp"
gdf_muni = gpd.read_file(os.path.join(DATAPATH, datafile)).to_crs('epsg:4326')

# Convert AGS from string to integer to ensure a clean join with the data table.
gdf_muni['AGS'] = gdf_muni['AGS'].astype(int)

# Load the DWD weather station locations as a point shapefile.
# These will be plotted as magenta dots on top of the choropleth map.
datafile = "stations.shp"
gdf_stations = gpd.read_file(os.path.join(DATAPATH, datafile))

# Merge the climate difference data onto the municipality GeoDataFrame.
# Outer join retains all municipalities even if some lack climate data.
gdf = gdf_muni.merge(df, on='AGS', how='outer')

# Define a diverging red-white-blue colour scale (seismic) centred on zero,
# with 0.5°C-wide bins from -3°C to +3°C.
# extend='both' adds arrows at both ends of the colorbar for values outside this range.
cmap = plt.cm.seismic
bounds = np.arange(-3., 3.5, 0.5)
norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
formatcode = '%.1f'  # One decimal place on colorbar tick labels

fig, ax = plt.subplots(figsize=(4,6))

# Add a vertical colorbar as a separate inset axis to the right of the map.
# [left, bottom, width, height] in figure coordinates (0–1).
ax2 = fig.add_axes([0.94, 0.16, 0.03, 0.68])
cb = mpl.colorbar.ColorbarBase(ax2, cmap=cmap, norm=norm,
                               spacing='uniform', ticks=bounds, boundaries=bounds, format=formatcode,
                               extend='both', orientation='vertical')
cb.ax.tick_params(labelsize='medium')
cb.set_label(label="Temperature at 2 metres (degree C)\nDWD grid minus DWD stations", size='medium')

# Layer 1: Draw municipality borders in black with no fill,
# providing a topographic reference frame for the map.
gdf_muni.plot(ax=ax, alpha=1., facecolor='none', lw=0.5, edgecolor='k')

# Layer 2: Fill each municipality with its temperature difference colour.
# lw=0.2 keeps thin borders visible; edgecolor='none' avoids double borders.
gdf.plot(ax=ax, alpha=1., column='diff_temperature_dwd', lw=0.2, cmap=cmap, norm=norm, edgecolor='none', markersize=1.)

# Layer 3: Overlay DWD station locations as small magenta dots
# so the spatial coverage of the station network is visible.
gdf_stations.plot(ax=ax, markersize=1., marker='o', color='m')

#ax.set_xlim(-130., 180.)
#ax.set_ylim(-60., 75.)

# Remove axis labels and coordinate ticks for a clean map appearance.
ax.set_xlabel(None)
ax.set_ylabel(None)
ax.set_xticks([])
ax.set_yticks([])
fig.savefig(os.path.join(FIGUREPATH, 'map_difference_DWD.png'), bbox_inches='tight', dpi=400)
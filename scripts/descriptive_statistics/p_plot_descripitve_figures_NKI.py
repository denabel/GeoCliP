#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
import os          # File path handling (os.path.join, os.path.exists, etc.)
import datetime    # Parsing and manipulating date/time objects

## ============================================================= ##
## THIRD-PARTY IMPORTS (require installation, see above)
## ============================================================= ##

# numpy: fundamental package for numerical computing in Python.
# Used here for array operations and bin edge construction (np.arange).
import numpy as np

# pandas: core library for tabular data manipulation.
# Used for loading CSVs, groupby aggregations, and merges.
import pandas as pd

# matplotlib: the base plotting library. pyplot provides a MATLAB-like
# interface for creating figures and axes. mpl (the top-level module)
# is imported separately to access lower-level objects like
# BoundaryNorm and ColorbarBase used in the choropleth map.
import matplotlib.pyplot as plt
import matplotlib as mpl

# seaborn: statistical visualisation library built on top of matplotlib.
# Provides higher-level plot types (distplot, barplot) with better
# default aesthetics.
import seaborn as sns

# geopandas: extends pandas to support geographic/spatial data.
# Used here to load and plot the German municipal boundary shapefile.
# Note: geopandas depends on shapely, fiona, and pyproj — these are
# installed automatically via conda-forge or pip.
import geopandas as gpd

## ============================================================= ##
## CONFIGURATION
## ============================================================= ##
# Base directory where input data files are located.
# './' means the current working directory (i.e. the folder you run
# the script from). Change these if your data/figures live elsewhere,
# e.g. DATAPATH = '/home/user/projects/NKI/data/'
DATAPATH = './'

# Directory where output figures will be saved.
FIGUREPATH = './'

## ============================================================= ##
## DATA LOADING
## ============================================================= ##
# Load the NKI (National Climate Initiative / Nationale Klimaschutzinitiative)
# project list from a semicolon-delimited CSV file.
#
# sep=';'             : German CSV exports typically use ';' as the delimiter
#                       instead of ',' because ',' is used as the decimal separator.
# encoding='latin-1' : Required for files containing German special characters
#                       (ä, ö, ü, ß). Use 'utf-8' if this raises a UnicodeDecodeError.
df = pd.read_csv(os.path.join(DATAPATH, 'NKI_full_list_06122023.csv'), sep=';', encoding='latin-1')

# Load the German municipal boundary shapefile (VG5000 dataset, reference date 31-Dec)
# into a GeoDataFrame for later spatial mapping.
# VG5000 is the official German topographic dataset at 1:5,000,000 scale,
# published by the Federal Agency for Cartography and Geodesy (BKG).
# VG5000_GEM.shp contains the municipality (Gemeinde) level boundaries.
datapath = os.path.join(DATAPATH, "vg5000_12-31.gk3.shape.ebenen/vg5000_ebenen_1231/")
datafile = "VG5000_GEM.shp"
gdf_districts = gpd.read_file(os.path.join(datapath, datafile))

## ============================================================= ##
## DATA CLEANING AND FEATURE EXTRACTION
## ============================================================= ##
# Many columns in this CSV were exported from Excel with a ="..." wrapper
# around each value (e.g. ="01.01.2010"). The lambda expressions below
# strip this wrapper with [2:-1] (removes leading =" and trailing ")
# before parsing the actual value.

# Parse the project start date string into a Python datetime object.
# strptime format '%d.%m.%Y' matches the German date format DD.MM.YYYY.
df['date_start'] = df['="Laufzeit von"'].apply(
  lambda x: datetime.datetime.strptime(x[2:-1].strip(), '%d.%m.%Y')
)

# Extract the calendar year as a plain integer for grouping and plotting.
df['year_start'] = df['date_start'].apply(lambda x: int(x.year))

# Clean the project type label:
#   x[2:-1]              : strip the ="..." Excel wrapper
#   .replace('KSI -', ''): remove the common 'KSI -' prefix
#   .strip()             : remove any remaining leading/trailing whitespace
df['project_type'] = df['="Klartext Leistungsplansystematik"'].apply(
  lambda x: x[2:-1].strip().replace('KSI -', '')
)

# Parse the funding amount from a German-formatted number string:
#   .replace('.', '')   : remove thousands separators (e.g. "1.234.567" → "1234567")
#   .replace(',', '.')  : replace decimal comma with decimal point ("1234,56" → "1234.56")
# Then divide by 1000 to convert from EUR to kEUR (thousands of EUR).
df['project_size'] = df['="Fördersumme in EUR"'].apply(
  lambda x: float(x.replace('.', '').replace(',', '.').strip())
) / 1000.

# Extract the Gemeindekennziffer (AGS — Amtlicher Gemeindeschlüssel),
# the official 8-digit German municipal district code, for merging with
# the shapefile later.
df['district_code'] = df['="Gemeindekennziffer"'].apply(lambda x: x[2:-1].strip())

## ============================================================= ##
## FIGURE 1: DISTRIBUTION OF PROJECT START YEARS
## ============================================================= ##
# Shows how many projects started in each year.
# np.arange(2005, 2023, 1) - 0.5 creates bin edges offset by 0.5 so that
# each bar is centred on a whole year (e.g. the bin for 2010 spans 2009.5–2010.5).
# Note: with stop=2023 the last bin edge is 2021.5, so only years up to 2021
# are shown — change to np.arange(2005, 2024, 1) to include 2022.
fig, ax = plt.subplots(figsize=(4, 4))
sns.distplot(df['year_start'].values, bins=np.arange(2005, 2023, 1) - 0.5)
ax.set_xlabel('First year of project')
ax.set_ylabel('Frequency')
ax.set_xticks(np.arange(2005, 2025 + 5, 5))  # Tick marks every 5 years
fig.savefig(os.path.join(FIGUREPATH, 'year_start.png'), bbox_inches='tight', dpi=400)

## ============================================================= ##
## FIGURE 2: DISTRIBUTION OF PROJECT FUNDING SIZES
## ============================================================= ##
# Histogram of project sizes in kEUR.
# The x-axis is capped at 500 kEUR (set_xlim) to focus on the bulk of
# the distribution; projects larger than 500 kEUR exist but are excluded
# visually to avoid compressing the main distribution.
# Bin width is 50 kEUR (np.arange(0, 550, 50)).
fig, ax = plt.subplots(figsize=(4, 4))
sns.distplot(df['project_size'].values, bins=np.arange(0, 500 + 50, 50))
ax.set_xlabel('Size of project (k EUR)')
ax.set_ylabel('Frequency')
ax.set_xticks(np.arange(0, 500 + 50, 50))
ax.set_xlim(0., 500)
fig.savefig(os.path.join(FIGUREPATH, 'project_size.png'), bbox_inches='tight', dpi=400)

## ============================================================= ##
## FIGURE 3: NUMBER OF PROJECTS PER PROJECT TYPE
## ============================================================= ##
# Aggregate project counts by category using groupby + count,
# then display as a horizontal bar chart (x=count, y=category name).
# year_start is used as the count column — any non-null column would give
# the same result since count() ignores NaNs.
dfc = df.groupby('project_type')['year_start'].count().reset_index()  # Count projects per type
fig, ax = plt.subplots(figsize=(6, 6))
sns.barplot(data=dfc, x='year_start', y='project_type')
ax.set_xlabel('Number of projects')
ax.set_ylabel('Type of project')
fig.savefig(os.path.join(FIGUREPATH, 'project_type.png'), bbox_inches='tight', dpi=400)

## ============================================================= ##
## FIGURE 4: TOTAL INVESTMENT PER PROJECT TYPE
## ============================================================= ##
# Sum the funding amounts per category (groupby + sum) and convert
# from kEUR to million EUR (÷ 1000) so the x-axis values stay compact.
# This shows where the bulk of NKI funding has been directed by policy area.
dfc = df.groupby('project_type')['project_size'].sum().reset_index()
dfc['project_size'] = dfc['project_size'] / 1e3  # kEUR → million EUR
fig, ax = plt.subplots(figsize=(6, 6))
sns.barplot(data=dfc, x='project_size', y='project_type')
ax.set_xlabel('Total investments (mil EUR)')
ax.set_ylabel('Type of project')
fig.savefig(os.path.join(FIGUREPATH, 'project_type_investment.png'), bbox_inches='tight', dpi=400)

## ============================================================= ##
## FIGURE 5: CHOROPLETH MAP OF PROJECT COUNTS BY MUNICIPALITY
## ============================================================= ##
# Count projects per district code and merge onto the GeoDataFrame
# using the AGS (Amtlicher Gemeindeschlüssel) key present in the shapefile.
# how='left' keeps all districts in the shapefile, even those with no projects.
dfc = df.groupby('district_code')['year_start'].count().reset_index()
gdf = gdf_districts.merge(dfc, left_on='AGS_0', right_on='district_code', how='left')

# Define a discrete green colour scale with 5-project-wide bins up to 50.
# BoundaryNorm maps data values to discrete colour levels.
# extend='max' adds an arrow at the top of the colorbar for counts > 50.
cmap = plt.cm.Greens
bounds = np.arange(0, 50 + 5, 5)
norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
formatcode = '%.0f'  # Display colorbar tick labels as integers (no decimal places)

fig, ax = plt.subplots(figsize=(6, 6))

# Add a vertical colorbar in a separate inset axis positioned to the right
# of the map. [left, bottom, width, height] in figure coordinates (0–1).
ax2 = fig.add_axes([0.85, 0.2, 0.03, 0.6])
cb = mpl.colorbar.ColorbarBase(
  ax2, cmap=cmap, norm=norm,
  spacing='uniform', ticks=bounds, boundaries=bounds, format=formatcode,
  extend='max', orientation='vertical'   # 'max' extension handles counts > 50
)
cb.ax.tick_params(labelsize='small')
cb.set_label(label="Number of projects", size='small')

ax.set_title(None)

# Layer 1: Draw all district outlines in grey as a base layer.
# This ensures districts with no data still appear on the map
# rather than showing as blank space.
gdf_districts.plot(ax=ax, alpha=1., facecolor='grey', lw=0.05, edgecolor='k')

# Layer 2: Fill districts present in the merged GeoDataFrame but
# with no project data (NaN after the left merge) with light grey (#D3D3D3).
gdf.plot(ax=ax, alpha=1., facecolor='#D3D3D3', lw=0., edgecolor='grey')

# Layer 3: Colour-fill districts that have project data using the
# Green choropleth scale. column='year_start' here holds the project
# count (renamed from the groupby result).
gdf.plot(ax=ax, alpha=1., column='year_start', lw=0., cmap=cmap, norm=norm, edgecolor='grey')

# Layer 4: Re-draw district borders on top so edges remain visible
# over the fill colours from layers 2 and 3.
gdf_districts.plot(ax=ax, alpha=1., facecolor='none', lw=0.05, edgecolor='k')

# Remove axis labels and coordinate tick labels for a clean map appearance.
ax.set_xlabel(None)
ax.set_ylabel(None)
ax.set_xticklabels([])
ax.set_yticklabels([])

fig.savefig(os.path.join(FIGUREPATH, 'map_projects.png'), bbox_inches='tight', dpi=400)

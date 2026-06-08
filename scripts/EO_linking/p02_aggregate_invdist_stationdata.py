#!/usr/bin/env python
# -*- coding: utf-8 -*-

## ============================================================= ##
## PACKAGE INSTALLATION
## ============================================================= ##
## Before running this script, make sure all required packages are
## installed in your Python environment. You can install them via pip:
##
##   pip install numpy pandas geopandas geopy
##
## Or via conda:
##
##   conda install numpy pandas
##   conda install -c conda-forge geopandas geopy
##
## Package versions this script was developed with (for reference):
##   Python    >= 3.8
##   numpy     >= 1.21
##   pandas    >= 1.3
##   geopandas >= 0.10
##   geopy     >= 2.2   (geodesic distance calculations)
##
## To check your currently installed versions, run:
##   pip show numpy pandas geopandas geopy
##
## NOTE ON RUNTIME:
## When CALCULATE_DISTANCES = True, this script computes pairwise
## geodesic distances between all municipalities and all stations.
## This can be slow (~hours) for large numbers of shapes and stations.
## Once computed, the distance matrix is saved to disk so subsequent
## runs can skip this step by setting CALCULATE_DISTANCES = False.
## ============================================================= ##

## ============================================================= ##
## STANDARD LIBRARY IMPORTS (no installation needed)
## ============================================================= ##
import sys   # System-specific parameters and functions
import os    # File path handling (os.path.join, etc.)
import copy  # Deep/shallow copying of objects
import ast   # Abstract Syntax Trees; available for safe literal evaluation if needed

## ============================================================= ##
## THIRD-PARTY IMPORTS (require installation, see above)
## ============================================================= ##

# numpy: fundamental package for numerical computing.
# Used here for matrix operations, distance matrix storage,
# and inverse-distance-weighted aggregation via np.dot.
import numpy as np

# pandas: core library for tabular data manipulation.
# Used for loading CSVs, groupby aggregations, merges, and saving output.
import pandas as pd

# geopandas: extends pandas to support geographic/spatial data.
# Used to load the municipality boundary shapefile and to create
# a GeoDataFrame of station point locations.
import geopandas as gpd

# geopy: library for geographic calculations.
# geodesic() computes the true surface distance between two
# lat/lon coordinate pairs, accounting for the Earth's curvature.
# This is more accurate than Euclidean distance for large areas.
from geopy.distance import geodesic

## ============================================================= ##
## CONFIGURATION
## ============================================================= ##
# Directory containing the DWD station CSV files and the imputed data file.
DATAPATH_DWD_STATIONS = './'

# Directory where the aggregated municipality-level output will be saved.
DATAPATH_AGGREGATED_MUNICIPALITY = './'

## ============================================================= ##
## PROCESSING PARAMETERS AND FLAGS
## ============================================================= ##
# Maximum distance (in km) within which a station contributes to a
# municipality's weighted average. Stations further than this cutoff
# are excluded (their weight is set to zero).
# A 100 km radius typically captures enough stations for robust
# interpolation across Germany while avoiding very distant stations.
DISTANCE_CUTOFF = 100 # in km

# AGGREGATE:
#   When True, runs the full spatial aggregation pipeline (distance
#   matrix, weight matrix, weighted averages). Set to False to skip.
AGGREGATE = True

# CALCULATE_DISTANCES:
#   When True, computes the full (n_municipalities × n_stations)
#   geodesic distance matrix and saves it to disk. This is slow —
#   set to False on subsequent runs to load the pre-computed matrix.
CALCULATE_DISTANCES = True

## ============================================================= ##
## VARIABLE SELECTION
## ============================================================= ##
# The climate variable to process. Must match the variable name used
# in the imputed data filename produced by the processing script.
variable = 'air_temperature'

## ============================================================= ##
## LOAD MUNICIPALITY BOUNDARY SHAPEFILE
## ============================================================= ##
# Load the VG250 German municipality boundary shapefile and reproject
# to WGS84 (EPSG:4326) so all coordinates are in decimal degrees.
# VG250 is the 1:250,000 scale official topographic dataset from BKG.
DATAPATH_SHAPES = './'

datafile = "VG250_GEM.shp"
gdf_shapes = gpd.read_file(os.path.join(DATAPATH_SHAPES, datafile)).to_crs('EPSG:4326')

# Compute the geographic centroid of each municipality polygon.
# These centroids are used as the reference points for distance
# calculations to the DWD weather stations.
gdf_shapes['centroid'] = gdf_shapes.centroid

## ============================================================= ##
## LOAD DWD STATION METADATA
## ============================================================= ##
# Load the station metadata table (station ID, lat, lon, elevation, name)
# produced by the download script. Rename 'station_id' to 'station'
# if necessary for consistency with the observation data columns.
datapath = os.path.join(DATAPATH_DWD_STATIONS)
datafile = 'stations.csv'
df_stations = pd.read_csv(os.path.join(datapath, datafile)).rename(columns={'station_id': 'station'})

## ============================================================= ##
## MAIN AGGREGATION PIPELINE
## ============================================================= ##
# The entire aggregation block is guarded by AGGREGATE = True
# to allow the script to be imported or partially run without
# triggering the full (potentially slow) computation.
if AGGREGATE == True:
  
  ## --------------------------------------------------------- ##
  ## LOAD IMPUTED DAILY MEAN DATA AND COMPUTE LONG-TERM MEANS
  ## --------------------------------------------------------- ##
  # Load the imputed daily mean temperature file produced by the
  # processing script (Stage 3, IMPUTATION_LASSO).
  datapath = os.path.join(DATAPATH_DWD_STATIONS)
datafile = 'dwd_cdc_hourly_2008-2023_{0:s}_daymean_imputed_lasso.csv'.format(variable)

df_daily = pd.read_csv(os.path.join(datapath, datafile))

# Compute the long-term mean for each station by averaging across all
# dates. This produces one representative value per station,
# which is then spatially interpolated to municipality level.
df_mean = df_daily.groupby('station').mean().reset_index()

# Define which columns contain the climate values to be aggregated.
# Only TT_TU (air temperature) is used here; RF_TU (humidity) is excluded.
value_columns = ['TT_TU']

## --------------------------------------------------------- ##
## FILTER TO MATCHING STATIONS
## --------------------------------------------------------- ##
# Keep only stations that are present in both the station metadata
# table and the imputed observations, ensuring a consistent set
# of stations for the distance matrix and aggregation.
dfs = df_stations.loc[df_stations['station'].isin(df_mean['station'].unique()), :].reset_index(drop=True)
df_mean = df_mean.loc[df_mean['station'].isin(dfs['station'].unique()), :].reset_index(drop=True)

# Print the number of stations available after filtering as a sanity check.
print('Number of stations: ', dfs['station'].nunique())

## --------------------------------------------------------- ##
## ASSIGN NUMERIC IDs AND ALIGN STATION ORDER
## --------------------------------------------------------- ##
# Assign a sequential integer ID to each station based on its row index.
# This ID is used to ensure the station order in df_mean matches
# the column order in the distance/weight matrices.
dfs['id'] = dfs.index.values
dfs = dfs.loc[:, ['station', 'id', 'lon', 'lat']]

# Merge the numeric ID onto the mean values DataFrame and sort by ID
# so that station order is consistent with the matrix columns.
df_mean = df_mean.merge(dfs.loc[:, ['station', 'id']], on='station', how='left')
df_mean = df_mean.sort_values(by=['id'], ascending=True).reset_index(drop=True)

## --------------------------------------------------------- ##
## CREATE GEODATAFRAME OF STATIONS AND SAVE AS SHAPEFILE
## --------------------------------------------------------- ##
# Convert the station metadata table to a GeoDataFrame by creating
# Point geometries from the lon/lat columns, then set CRS to WGS84.
gdf_stations = gpd.GeoDataFrame(dfs, geometry=gpd.points_from_xy(dfs.lon, dfs.lat)).set_crs('EPSG:4326')

# Save the station locations as a shapefile for use in mapping scripts
# (e.g. as the magenta station dots in the temperature difference map).
gdf_stations.to_file(os.path.join(DATAPATH_OUT, 'stations.shp'))

# Store the number of municipalities and stations for matrix dimensions.
# Step 3: Create a weight matrix (n_shapes x n_points)
n_shapes = len(gdf_shapes)
n_points = len(gdf_stations)

## --------------------------------------------------------- ##
## COMPUTE OR LOAD GEODESIC DISTANCE MATRIX
## --------------------------------------------------------- ##
if CALCULATE_DISTANCES == True:
  
  print('Calculating distance matrix...')

# Initialise a zero matrix of shape (n_municipalities × n_stations).
# Entry [i, j] will hold the geodesic distance in km between
# the centroid of municipality i and station j.
distance_matrix = np.zeros((n_shapes, n_points))
minimum_distances = []

# Calculate geodesic distances and inverse distance weights
# Loop over all municipality centroids (outer loop) and all
# station locations (inner loop) to fill the distance matrix.
# geodesic() takes (lat, lon) tuples and returns a Distance object;
# .meters / 1000 converts to kilometres.
for i, shape in gdf_shapes.iterrows():
  
  print(i)  # Progress indicator (municipality index)

# Extract the centroid coordinates as (latitude, longitude).
centroid = (shape['centroid'].y, shape['centroid'].x)
distances = []

for j, point in gdf_stations.iterrows():
  point_coords = (point.geometry.y, point.geometry.x)
distance = geodesic(centroid, point_coords).meters / 1000.
distance_matrix[i, j] = distance

# Save the computed distance matrix to a text file so it can be
# reloaded on subsequent runs without recomputing.
np.savetxt(os.path.join(DATAPATH_OUT, 'distance_matrix_gemeinde.txt'), distance_matrix, delimiter=',')

# Set flag to False so the distance matrix is not recomputed
# if this script continues further in the same session.
CALCULATE_DISTANCES = False

else:
  # Load a previously computed distance matrix from disk.
  # This skips the slow double loop above.
  distance_matrix = np.loadtxt(os.path.join(DATAPATH_OUT, 'distance_matrix_gemeinde.txt'), delimiter=',')

## --------------------------------------------------------- ##
## APPLY DISTANCE CUTOFF AND COMPUTE INVERSE DISTANCE WEIGHTS
## --------------------------------------------------------- ##
# Set all distances greater than DISTANCE_CUTOFF (100 km) to zero.
# This excludes distant stations from the weighted average entirely,
# ensuring that only nearby stations influence each municipality.
distance_matrix[distance_matrix > DISTANCE_CUTOFF] = 0.

# Compute inverse-distance weights: closer stations receive higher weight.
# Dividing each row by its row sum normalises the weights so they
# sum to 1 per municipality, producing a proper weighted average.
# keepdims=True preserves the (n_shapes, 1) shape for broadcasting.
weight_matrix = distance_matrix / distance_matrix.sum(axis=1, keepdims=True)

## --------------------------------------------------------- ##
## AGGREGATE STATION VALUES TO MUNICIPALITY LEVEL
## --------------------------------------------------------- ##
print('Aggregating from stations to districts...')

for i, value_column in enumerate(value_columns):
  
  # Create a value matrix (n_points x n_timesteps)
  # Pivot the df to create a matrix of values, with rows as time steps and columns as point IDs
  # Here df_mean[value_column].values is a 1D array (one mean value per station).
  value_matrix = df_mean[value_column].values

# Perform matrix multiplication to get the weighted averages for each shape and time step
# np.dot(weight_matrix, value_matrix.T) computes, for each municipality,
# the sum of (weight × station_value) across all stations within the cutoff radius.
# Result: a 1D array of length n_municipalities.
weighted_avg_matrix = np.dot(weight_matrix, value_matrix.T)  # Multiply weight matrix with value matrix

# Store the result in a DataFrame indexed by the official AGS municipality code.
df_agg = pd.DataFrame(weighted_avg_matrix, columns=[value_column], index=gdf_shapes['AGS'].values).reset_index().rename(columns={'index': 'AGS'})

if i == 0:
  # First variable: initialise the combined output DataFrame.
  df_new = df_agg.copy()
else:
  # Subsequent variables: merge on AGS to add the new column.
  df_new = df_new.merge(df_agg, on=['AGS'], how='outer')

## --------------------------------------------------------- ##
## SAVE AGGREGATED MUNICIPALITY-LEVEL OUTPUT
## --------------------------------------------------------- ##
# Save the final municipality-level aggregated climate data.
# The filename encodes the distance cutoff used, making it easy to
# identify which interpolation radius produced the file.
datapath = os.path.join(DATAPATH_OUT)
datafile = 'data_gemeinde_2008-2023_air_temperature_daymean_invdistances_{0:d}km.csv'.format(DISTANCE_CUTOFF)
df_new.to_csv(os.path.join(datapath, datafile), index=False)
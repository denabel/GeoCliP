#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import copy
import ast

import numpy as np
import pandas as pd

import geopandas as gpd
from geopy.distance import geodesic

## ============================================================================================= ##

DATAPATH_DWD_STATIONS = './'
DATAPATH_AGGREGATED_MUNICIPALITY = './'

## ============================================================================================= ##

DISTANCE_CUTOFF = 100 # in km

AGGREGATE = True
CALCULATE_DISTANCES = True

## =============================== ##

variable = 'air_temperature'

## ============================================================================================= ##

DATAPATH_SHAPES = './'

datafile = "VG250_GEM.shp"
gdf_shapes = gpd.read_file(os.path.join(DATAPATH_SHAPES, datafile)).to_crs('EPSG:4326')
gdf_shapes['centroid'] = gdf_shapes.centroid

## ============================================================================================= ##

datapath = os.path.join(DATAPATH_DWD_STATIONS)
datafile = 'stations.csv'
df_stations = pd.read_csv(os.path.join(datapath, datafile)).rename(columns={'station_id': 'station'})

## ============================================================================================= ##

if AGGREGATE == True:

	datapath = os.path.join(DATAPATH_DWD_STATIONS)
	datafile = 'dwd_cdc_hourly_2008-2023_{0:s}_daymean_imputed_lasso.csv'.format(variable)

	df_daily = pd.read_csv(os.path.join(datapath, datafile))
	df_mean = df_daily.groupby('station').mean().reset_index()

	value_columns = ['TT_TU']

	## =============================== ##

	dfs = df_stations.loc[df_stations['station'].isin(df_mean['station'].unique()), :].reset_index(drop=True)
	df_mean = df_mean.loc[df_mean['station'].isin(dfs['station'].unique()), :].reset_index(drop=True)
	print('Number of stations: ', dfs['station'].nunique())

	## =============================== ##

	dfs['id'] = dfs.index.values
	dfs = dfs.loc[:, ['station', 'id', 'lon', 'lat']]

	df_mean = df_mean.merge(dfs.loc[:, ['station', 'id']], on='station', how='left')
	df_mean = df_mean.sort_values(by=['id'], ascending=True).reset_index(drop=True)

	## =============================== ##

	gdf_stations = gpd.GeoDataFrame(dfs, geometry=gpd.points_from_xy(dfs.lon, dfs.lat)).set_crs('EPSG:4326')
	gdf_stations.to_file(os.path.join(DATAPATH_OUT, 'stations.shp'))

	# Step 3: Create a weight matrix (n_shapes x n_points)
	n_shapes = len(gdf_shapes)
	n_points = len(gdf_stations)

	## =============================== ##

	if CALCULATE_DISTANCES == True:

		print('Calculating distance matrix...')

		distance_matrix = np.zeros((n_shapes, n_points))
		minimum_distances = []

		# Calculate geodesic distances and inverse distance weights
		for i, shape in gdf_shapes.iterrows():

			print(i)

			centroid = (shape['centroid'].y, shape['centroid'].x)
			distances = []

			for j, point in gdf_stations.iterrows():
				point_coords = (point.geometry.y, point.geometry.x)
				distance = geodesic(centroid, point_coords).meters / 1000.
				distance_matrix[i, j] = distance

		np.savetxt(os.path.join(DATAPATH_OUT, 'distance_matrix_gemeinde.txt'), distance_matrix, delimiter=',')

		CALCULATE_DISTANCES = False

	else:
		distance_matrix = np.loadtxt(os.path.join(DATAPATH_OUT, 'distance_matrix_gemeinde.txt'), delimiter=',')

	## =============================== ##

	distance_matrix[distance_matrix > DISTANCE_CUTOFF] = 0.

	weight_matrix = distance_matrix / distance_matrix.sum(axis=1, keepdims=True)

	## =============================== ##

	print('Aggregating from stations to districts...')

	for i, value_column in enumerate(value_columns):

		# Create a value matrix (n_points x n_timesteps)
		# Pivot the df to create a matrix of values, with rows as time steps and columns as point IDs
		value_matrix = df_mean[value_column].values

		# Perform matrix multiplication to get the weighted averages for each shape and time step
		weighted_avg_matrix = np.dot(weight_matrix, value_matrix.T)  # Multiply weight matrix with value matrix
		df_agg = pd.DataFrame(weighted_avg_matrix, columns=[value_column], index=gdf_shapes['AGS'].values).reset_index().rename(columns={'index': 'AGS'})

		if i == 0:
			df_new = df_agg.copy()
		else:
			df_new = df_new.merge(df_agg, on=['AGS'], how='outer')

	datapath = os.path.join(DATAPATH_OUT)
	datafile = 'data_gemeinde_2008-2023_air_temperature_daymean_invdistances_{0:d}km.csv'.format(DISTANCE_CUTOFF)
	df_new.to_csv(os.path.join(datapath, datafile), index=False)

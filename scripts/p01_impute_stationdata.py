#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import datetime
import numpy as np
import pandas as pd
import geopandas as gpd

## ============================================================================================= ##

DATAPATH_DWD_STATIONS = './'

## ============================================================================================= ##

MERGE = False
IMPUTATION_LASSO = False

for variable in ['air_temperature']:

	## ============================================================================================= ##

	if variable == 'air_temperature':
		value_columns = ['TT_TU', 'RF_TU']

	variable_filelabel = {\
		'air_temperature': 'TU',
		}

	## ============================================================================================= ##

	def expand_df(df, dims, values):
		df = df.set_index(dims)
		multi_index = (pd.MultiIndex.from_product(
				iterables=values,
				names=dims))
		df = df.reindex(multi_index, fill_value=np.nan).reset_index()
		df = df.sort_values(by=dims, ascending=True).reset_index(drop=True)
		return df

	## ============================================================================================= ##

	if MERGE == True:

		datapath = os.path.join(DATAPATH_DWD_STATIONS)
		df_files = pd.DataFrame({'filename': [f for f in os.listdir(datapath) if (('dwd_cdc_' in f) and (variable_filelabel[variable] in f) and ('imputed' not in f))]})
		df_files['date_range'] = df_files['filename'].apply(lambda x: x.split('_')[-1].split('.csv')[0])
		df_files['year_last'] = df_files['date_range'].apply(lambda x: int(x.split('-')[1][:4]))
		df_files['year_first'] = df_files['date_range'].apply(lambda x: int(x.split('-')[0][:4]))
		df_files = df_files.loc[df_files['year_last'] == 2023, :]
		df_files = df_files.loc[df_files['year_first'] <= 2005, :]
		df_files['station'] = df_files['filename'].apply(lambda x: x.split(variable)[-1].split('_')[2])
		df_files = df_files.reset_index()

		## ============================================================================================= ##

		df_all = pd.DataFrame()

		for i, row in df_files.iterrows():

			print(i)
			df = pd.read_csv(os.path.join(datapath, row['filename']))
			df['station'] = row['station']
			df = df.replace(-999., np.nan)
			df['hour'] = df['datetime'].astype(str).apply(lambda x: int(x[-2:]))
			df['date'] = df['datetime'].astype(int).astype(str).apply(lambda x: datetime.datetime.strptime(x[:-2], "%Y%m%d"))
			df['date'] = df['date'].apply(lambda x: datetime.datetime.strftime(x, "%Y%m%d"))

			df['nobs'] = df.groupby(['station', 'date'])['TT_TU'].transform(lambda x: x.count())
			df = df.loc[df['nobs'] == 24, :].drop(columns='nobs')

			df = df.groupby(['station', 'date']).mean().reset_index()
			df['year'] = df['date'].astype(str).apply(lambda x: int(x[:4]))
			df = df.loc[df['year'] >= 2008, :]
			df = df.loc[df['year'] < 2024, :]

			print(row['station'], df.groupby(['year'])['TT_TU'].count())

			df = df.drop(columns=['year', 'hour', 'datetime']).rename(columns={'date': 'datetime'})
			df_all = pd.concat([df_all, df], axis=0, ignore_index=True)

		df_all.to_csv(os.path.join(datapath, 'dwd_cdc_hourly_2008-2023_{0:s}_daymean.csv'.format(variable)), index=False)

	## ============================================================================================= ##

	datapath = os.path.join(DATAPATH_DWD_STATIONS)
	df = pd.read_csv(os.path.join(datapath, 'dwd_cdc_hourly_2008-2023_{0:s}_daymean.csv'.format(variable)))

	## identify missing values
	df = df.replace(-999., np.nan)

	## expand data frame
	datetimes = df['datetime'].unique()
	datetimes.sort()
	stations = df['station'].unique()
	stations.sort()
	df = expand_df(df, ['station', 'datetime'], [stations, datetimes])

	## account for quality flags

	## nothing to do, see data description from DWD. all values seem to have been checked and if needed corrected

	datapath = os.path.join(DATAPATH_DWD_STATIONS)
	datafile = 'dwd_cdc_hourly_2008-2023_{0:s}_daymean_expanded.csv'.format(variable)
	df.to_csv(os.path.join(datapath, datafile), index=False)

	## ============================================================================================= ##

	from sklearn.linear_model import LassoCV

	if IMPUTATION_LASSO == True:

		for i, value_column in enumerate(value_columns):

			print(value_column)

			# Step 1: Pivot the dataframe such that rows correspond to time steps and columns to units
			df_pivot = df.pivot(index='datetime', columns='station', values=value_column)

			# Step 2: Randomly sample a subset of time steps for training (e.g., 50% of the time steps)
			np.random.seed(0)
			sampled_times = np.random.choice(df_pivot.index, size=int(len(df_pivot) * 0.1), replace=False)

			# Extract the sampled time steps (all units for those time steps)
			df_sampled = df_pivot.loc[sampled_times]

			# Step 3: Use LassoCV as the estimator for sparse imputation
			lasso_estimator = LassoCV(cv=10, random_state=0, tol=1.e-2)  # Cross-validated Lasso for optimal regularization

			# Step 4: Initialize IterativeImputer with LassoCV for sparse imputation
			imputer = IterativeImputer(estimator=lasso_estimator, max_iter=100, random_state=0)

			# Train the imputer on the sampled data
			imputer.fit(df_sampled)

			# Step 5: Apply imputation to the full dataset, time step by time step
			def impute_time_step(df_group, imputer):
			    """
			    Impute missing values for a specific time step using the trained LassoCV-based imputer.
			    """
			    data = df_group.values.reshape(1, -1)  # Reshape for single-row transformation
			    imputed_values = imputer.transform(data)
			    df_group[:] = imputed_values.reshape(-1)  # Replace the missing values in the group
			    return df_group

			# Impute the missing values time step by time step on the full dataset
			df_imputed = df_pivot.apply(lambda row: impute_time_step(row, imputer), axis=1)

			# Step 6: Convert back to the original long format
			df_imputed_long = df_imputed.stack().reset_index(name=value_column)

			datapath = os.path.join(DATAPATH_DWD_STATIONS)
			datafile = 'dwd_cdc_hourly_2008-2023_{0:s}_daymean_imputed_lasso_{1:s}.csv'.format(variable, value_column)
			df_imputed_long.to_csv(os.path.join(datapath, datafile), index=False)

		for i, value_column in enumerate(value_columns):

			datapath = os.path.join(DATAPATH_DWD_STATIONS)
			datafile = 'dwd_cdc_hourly_2008-2023_{0:s}_daymean_imputed_lasso_{1:s}.csv'.format(variable, value_column)
			df_imputed_long = pd.read_csv(os.path.join(datapath, datafile))

			if i == 0:
				df_imputed_allvars = df_imputed_long.copy()
			else:
				df_imputed_allvars = df_imputed_allvars.merge(df_imputed_long, on=['datetime', 'station'], how='outer')

		datapath = os.path.join(DATAPATH_DWD_STATIONS)
		datafile = 'dwd_cdc_hourly_2008-2023_{0:s}_daymean_imputed_lasso.csv'.format(variable)
		df_imputed_allvars.to_csv(os.path.join(datapath, datafile), index=False)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

## ============================================================= ##
## PACKAGE INSTALLATION
## ============================================================= ##
## Before running this script, make sure all required packages are
## installed in your Python environment. You can install them via pip:
##
##   pip install numpy pandas geopandas scikit-learn
##
## Or via conda:
##
##   conda install numpy pandas geopandas
##   conda install -c conda-forge scikit-learn
##
## Package versions this script was developed with (for reference):
##   Python       >= 3.8
##   numpy        >= 1.21
##   pandas       >= 1.3
##   geopandas    >= 0.10
##   scikit-learn >= 1.0   (only needed when IMPUTATION_LASSO = True)
##
## To check your currently installed versions, run:
##   pip show numpy pandas geopandas scikit-learn
## ============================================================= ##

## ============================================================= ##
## STANDARD LIBRARY IMPORTS (no installation needed)
## ============================================================= ##
import os        # File path handling (os.path.join, os.listdir, etc.)
import datetime  # Parsing and formatting date strings

## ============================================================= ##
## THIRD-PARTY IMPORTS (require installation, see above)
## ============================================================= ##

# numpy: fundamental package for numerical computing.
# Used for NaN filling, random sampling, and array reshaping.
import numpy as np

# pandas: core library for tabular data manipulation.
# Used throughout for loading, merging, grouping, and saving CSV files.
import pandas as pd

# geopandas: extends pandas to support geographic/spatial data.
# Imported here but used in downstream scripts; kept for consistency
# with the broader project environment.
import geopandas as gpd

## ============================================================= ##
## CONFIGURATION
## ============================================================= ##
# Directory containing the individual station CSV files produced by
# the download script, and where all output files will be saved.
DATAPATH_DWD_STATIONS = './'

## ============================================================= ##
## PROCESSING FLAGS
## ============================================================= ##
# These two boolean flags control which processing stages are executed.
# Set to True to run the corresponding stage, False to skip it.
#
# MERGE:
#   When True, reads all individual per-station CSV files, computes
#   daily means, and merges them into a single combined CSV file.
#   Set to False once the merged file has been created to avoid
#   reprocessing — this stage can be slow with many station files.
#
# IMPUTATION_LASSO:
#   When True, fills missing values in the merged dataset using a
#   LassoCV-based iterative imputation approach (see details below).
#   Set to False to skip imputation and work with the raw merged data.
MERGE = False
IMPUTATION_LASSO = False

## ============================================================= ##
## MAIN PROCESSING LOOP
## ============================================================= ##
# Loop over climate variables to be processed.
# Currently only 'air_temperature' is active; additional variables
# (e.g. 'precipitation') can be added to this list if needed.
for variable in ['air_temperature']:
  
  ## --------------------------------------------------------- ##
  ## VARIABLE-SPECIFIC SETTINGS
  ## --------------------------------------------------------- ##
  # Define which measurement columns are relevant for this variable.
  # For air_temperature:
  #   TT_TU : air temperature at 2 m height (degrees Celsius)
  #   RF_TU : relative humidity (%)
  if variable == 'air_temperature':
  value_columns = ['TT_TU', 'RF_TU']

# Mapping from variable name to the DWD file label used in filenames.
# DWD uses 'TU' (Temperatur und Feuchte) as the file label for air temperature.
variable_filelabel = {\
  'air_temperature': 'TU',
}

## --------------------------------------------------------- ##
## HELPER FUNCTION: EXPAND DATAFRAME TO FULL GRID
## --------------------------------------------------------- ##
def expand_df(df, dims, values):
  # Expand a DataFrame to include ALL combinations of the given dimensions,
  # filling any missing combinations with NaN.
  # This ensures the dataset has a complete regular grid of
  # (station × datetime) pairs, even where observations are missing.
  #
  # Parameters:
  #   df     : input DataFrame
  #   dims   : list of column names to use as index dimensions
  #   values : list of iterables with all desired values per dimension
  #
  # Returns:
  #   DataFrame with one row per combination, sorted ascending by dims.
  df = df.set_index(dims)
multi_index = (pd.MultiIndex.from_product(
  iterables=values,
  names=dims))
df = df.reindex(multi_index, fill_value=np.nan).reset_index()
df = df.sort_values(by=dims, ascending=True).reset_index(drop=True)
return df

## ============================================================= ##
## STAGE 1: MERGE INDIVIDUAL STATION FILES INTO ONE COMBINED FILE
## ============================================================= ##
# This stage is only executed when MERGE = True.
# It reads all per-station CSV files in DATAPATH_DWD_STATIONS,
# computes daily means from the hourly data, and concatenates
# everything into a single long-format CSV file.
if MERGE == True:
  
  datapath = os.path.join(DATAPATH_DWD_STATIONS)

## ----------------------------------------------------- ##
## BUILD FILE LIST AND FILTER BY DATE RANGE
## ----------------------------------------------------- ##
# Scan the data directory for files matching the pattern:
#   - contain 'dwd_cdc_' (DWD Climate Data Center prefix)
#   - contain the variable file label (e.g. 'TU' for air temperature)
#   - do not contain 'imputed' (exclude previously imputed files)
df_files = pd.DataFrame({'filename': [f for f in os.listdir(datapath) if (('dwd_cdc_' in f) and (variable_filelabel[variable] in f) and ('imputed' not in f))]})

# Extract the date range from the filename.
# DWD filenames end with YYYYMMDD-YYYYMMDD.csv; split to get the range string.
df_files['date_range'] = df_files['filename'].apply(lambda x: x.split('_')[-1].split('.csv')[0])

# Extract the last and first year from the date range string.
# x.split('-')[1][:4] takes the first 4 characters of the end date (year).
df_files['year_last']  = df_files['date_range'].apply(lambda x: int(x.split('-')[1][:4]))
df_files['year_first'] = df_files['date_range'].apply(lambda x: int(x.split('-')[0][:4]))

# Keep only stations whose data extends to 2023 (complete recent record)
# and starts no later than 2005 (sufficient historical coverage).
df_files = df_files.loc[df_files['year_last']  == 2023, :]
df_files = df_files.loc[df_files['year_first'] <= 2005, :]

# Extract the station ID from the filename.
# The station ID follows the variable label in the filename,
# e.g. '...air_temperature_01234_...' → station = '01234'
df_files['station'] = df_files['filename'].apply(lambda x: x.split(variable)[-1].split('_')[2])
df_files = df_files.reset_index()

## ----------------------------------------------------- ##
## LOOP OVER STATIONS AND COMPUTE DAILY MEANS
## ----------------------------------------------------- ##
# Initialise an empty DataFrame to accumulate all station data.
df_all = pd.DataFrame()

for i, row in df_files.iterrows():
  
  print(i)  # Progress indicator

# Load the hourly station data CSV.
df = pd.read_csv(os.path.join(datapath, row['filename']))

# Attach the station ID as a column for later grouping.
df['station'] = row['station']

# Replace DWD's missing value code (-999.) with NaN so that
# pandas aggregation functions handle them correctly.
df = df.replace(-999., np.nan)

# Extract the hour (last two digits of the YYYYMMDDHH timestamp)
# for use in the completeness check below.
df['hour'] = df['datetime'].astype(str).apply(lambda x: int(x[-2:]))

# Parse the date portion of the timestamp (all digits except the last two)
# and reformat as a YYYYMMDD string for daily grouping.
df['date'] = df['datetime'].astype(int).astype(str).apply(lambda x: datetime.datetime.strptime(x[:-2], "%Y%m%d"))
df['date'] = df['date'].apply(lambda x: datetime.datetime.strftime(x, "%Y%m%d"))

# Count the number of hourly observations per (station, date).
# transform() keeps the count aligned with the original DataFrame rows.
df['nobs'] = df.groupby(['station', 'date'])['TT_TU'].transform(lambda x: x.count())

# Keep only days with a full 24-hour record to avoid biased daily means.
# Drop the helper column nobs after filtering.
df = df.loc[df['nobs'] == 24, :].drop(columns='nobs')

# Compute daily mean values by averaging all 24 hourly observations
# per (station, date) pair.
df = df.groupby(['station', 'date']).mean().reset_index()

# Extract the year for filtering.
df['year'] = df['date'].astype(str).apply(lambda x: int(x[:4]))

# Restrict to the analysis period 2008–2023 (inclusive).
# year < 2024 excludes any partial 2024 data.
df = df.loc[df['year'] >= 2008, :]
df = df.loc[df['year'] < 2024, :]

# Print the number of valid daily observations per year as a quality check.
print(row['station'], df.groupby(['year'])['TT_TU'].count())

# Remove helper columns and rename 'date' back to 'datetime'
# so the output column name is consistent across all stations.
df = df.drop(columns=['year', 'hour', 'datetime']).rename(columns={'date': 'datetime'})

# Append this station's data to the combined DataFrame.
df_all = pd.concat([df_all, df], axis=0, ignore_index=True)

# Save the merged daily mean data for all stations to a single CSV file.
# Filename encodes the variable name for easy identification.
df_all.to_csv(os.path.join(datapath, 'dwd_cdc_hourly_2008-2023_{0:s}_daymean.csv'.format(variable)), index=False)

## ============================================================= ##
## STAGE 2: LOAD MERGED DATA AND EXPAND TO FULL GRID
## ============================================================= ##
# This stage always runs (regardless of MERGE flag).
# It loads the merged daily mean file and expands it to a complete
# regular (station × datetime) grid, filling gaps with NaN.

datapath = os.path.join(DATAPATH_DWD_STATIONS)

# Load the combined daily mean file produced by Stage 1 (or a pre-existing one).
df = pd.read_csv(os.path.join(datapath, 'dwd_cdc_hourly_2008-2023_{0:s}_daymean.csv'.format(variable)))

## identify missing values
# Replace any remaining -999. sentinel values with NaN.
df = df.replace(-999., np.nan)

## expand data frame
# Get the sorted unique lists of all datetimes and stations present in the data.
# These define the full grid dimensions for expand_df.
datetimes = df['datetime'].unique()
datetimes.sort()
stations = df['station'].unique()
stations.sort()

# Expand to the full (station × datetime) grid.
# Missing combinations (station-date pairs without an observation) are filled with NaN.
df = expand_df(df, ['station', 'datetime'], [stations, datetimes])

## account for quality flags
## nothing to do, see data description from DWD. all values seem to have been checked and if needed corrected

# Save the expanded (complete grid) dataset.
datapath = os.path.join(DATAPATH_DWD_STATIONS)
datafile = 'dwd_cdc_hourly_2008-2023_{0:s}_daymean_expanded.csv'.format(variable)
df.to_csv(os.path.join(datapath, datafile), index=False)

## ============================================================= ##
## STAGE 3: MISSING VALUE IMPUTATION USING LASSO REGRESSION
## ============================================================= ##
# LassoCV is imported here rather than at the top of the script
# because it is only needed when IMPUTATION_LASSO = True.
# scikit-learn is a large dependency and this avoids loading it unnecessarily.
from sklearn.linear_model import LassoCV

# This stage is only executed when IMPUTATION_LASSO = True.
# It fills NaN values in the expanded dataset using an iterative imputation
# approach where each station's missing values are predicted from the
# observed values of all other stations at the same time step,
# using a cross-validated Lasso (L1-regularised linear regression) model.
if IMPUTATION_LASSO == True:
  
  ## ----------------------------------------------------- ##
  ## IMPUTE EACH VARIABLE COLUMN SEPARATELY
  ## ----------------------------------------------------- ##
  for i, value_column in enumerate(value_columns):
  
  print(value_column)

# Step 1: Pivot the dataframe such that rows correspond to time steps and columns to units
# Result: a wide-format matrix of shape (n_datetimes × n_stations).
df_pivot = df.pivot(index='datetime', columns='station', values=value_column)

# Step 2: Randomly sample a subset of time steps for training (e.g., 50% of the time steps)
# Using 10% of time steps keeps training fast while still capturing
# the cross-station correlation structure.
# random_seed=0 ensures reproducibility.
np.random.seed(0)
sampled_times = np.random.choice(df_pivot.index, size=int(len(df_pivot) * 0.1), replace=False)

# Extract the sampled time steps (all units for those time steps)
df_sampled = df_pivot.loc[sampled_times]

# Step 3: Use LassoCV as the estimator for sparse imputation
# cv=10 : 10-fold cross-validation to select the optimal regularisation strength
# tol   : convergence tolerance; relaxed slightly (1e-2) to speed up fitting
lasso_estimator = LassoCV(cv=10, random_state=0, tol=1.e-2)  # Cross-validated Lasso for optimal regularization

# Step 4: Initialize IterativeImputer with LassoCV for sparse imputation
# IterativeImputer models each feature (station) as a function of all others,
# iterating until convergence (up to max_iter=100 rounds).
imputer = IterativeImputer(estimator=lasso_estimator, max_iter=100, random_state=0)

# Train the imputer on the sampled data
# The imputer learns the inter-station regression relationships
# from the subsample of complete and partially-complete time steps.
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
# axis=1 applies the function row-wise (one time step at a time).
df_imputed = df_pivot.apply(lambda row: impute_time_step(row, imputer), axis=1)

# Step 6: Convert back to the original long format
# stack() converts the wide (datetime × station) matrix back to long format;
# reset_index() turns the MultiIndex into regular columns.
df_imputed_long = df_imputed.stack().reset_index(name=value_column)

# Save the imputed data for this variable column to a CSV file.
datapath = os.path.join(DATAPATH_DWD_STATIONS)
datafile = 'dwd_cdc_hourly_2008-2023_{0:s}_daymean_imputed_lasso_{1:s}.csv'.format(variable, value_column)
df_imputed_long.to_csv(os.path.join(datapath, datafile), index=False)

## ----------------------------------------------------- ##
## MERGE ALL IMPUTED VARIABLE COLUMNS INTO ONE FILE
## ----------------------------------------------------- ##
# After imputing each variable column separately, reload the
# individual imputed files and merge them into a single wide CSV
# with all variables as columns, joined on (datetime, station).
for i, value_column in enumerate(value_columns):
  
  datapath = os.path.join(DATAPATH_DWD_STATIONS)
datafile = 'dwd_cdc_hourly_2008-2023_{0:s}_daymean_imputed_lasso_{1:s}.csv'.format(variable, value_column)
df_imputed_long = pd.read_csv(os.path.join(datapath, datafile))

if i == 0:
  # First variable: initialise the combined DataFrame.
  df_imputed_allvars = df_imputed_long.copy()
else:
  # Subsequent variables: merge on the shared (datetime, station) key.
  df_imputed_allvars = df_imputed_allvars.merge(df_imputed_long, on=['datetime', 'station'], how='outer')

# Save the final merged imputed dataset containing all variable columns.
datapath = os.path.join(DATAPATH_DWD_STATIONS)
datafile = 'dwd_cdc_hourly_2008-2023_{0:s}_daymean_imputed_lasso.csv'.format(variable)
df_imputed_allvars.to_csv(os.path.join(datapath, datafile), index=False)
#!/usr/bin/env python
# -*- coding: utf-8 -*-

## ============================================================= ##
## PACKAGE INSTALLATION
## ============================================================= ##
## Before running this script, make sure all required packages are
## installed in your Python environment. You can install them via pip:
##
##   pip install pandas
##
## The other packages used (os, zipfile, urllib.request) are part of
## the Python standard library and do not need to be installed separately.
##
## Package versions this script was developed with (for reference):
##   Python >= 3.8
##   pandas >= 1.3
##
## To check your currently installed version, run:
##   pip show pandas
##
## INTERNET ACCESS REQUIRED:
## This script downloads data directly from the DWD (Deutscher Wetterdienst)
## open data server. Make sure you have an active internet connection
## and that the DWD CDC server is reachable.
## ============================================================= ##

## ============================================================= ##
## STANDARD LIBRARY IMPORTS (no installation needed)
## ============================================================= ##
import os              # File path handling (os.path.join, os.remove, etc.)
import zipfile         # Reading and extracting .zip archive files
import urllib.request  # Downloading files from URLs over HTTP/HTTPS

## ============================================================= ##
## THIRD-PARTY IMPORTS (require installation, see above)
## ============================================================= ##

# pandas: core library for tabular data manipulation.
# Used here for parsing the file listing, building per-station DataFrames,
# and writing output CSV files.
import pandas as pd

## ============================================================= ##
## CONFIGURATION
## ============================================================= ##
# Directory where downloaded station CSV files and the final stations.csv
# will be saved. './' means the current working directory.
# Change this to a dedicated folder if needed, e.g.:
# DATAPATH_DWD_STATIONS = '/home/user/projects/climate/dwd_stations/'
DATAPATH_DWD_STATIONS = './'

## ============================================================= ##
## DATA SOURCE: DWD CDC OPEN DATA SERVER
## ============================================================= ##
# Base URL of the DWD Climate Data Center (CDC) open data directory
# for hourly air temperature observations (historical data, all stations).
# The server provides an HTML index page that lists all available zip files.
# DWD open data is freely accessible without registration.
base_url = 'https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/air_temperature/historical/'

## ============================================================= ##
## PARSE FILE LISTING FROM DWD SERVER
## ============================================================= ##
# Read the HTML index page of the DWD directory as if it were a CSV.
# pandas reads each line of the HTML as a row, which allows us to
# extract the href links to the individual station zip files.
filelist = pd.read_csv(base_url)

# Parse the raw HTML lines to extract only the zip filenames.
# - Filter lines containing 'stundenwerte' (German for 'hourly values')
#   to skip non-data links (parent directory, readme files, etc.)
# - Extract the filename from the href="..." attribute of each anchor tag:
#     split("href=")[1]  → everything after href=
#     split('>')[0]      → everything before the closing >
#     [1:-1]             → strip the surrounding quote characters
filelist = [c.split("href=")[1].split('>')[0][1:-1] for c in filelist.iloc[:, 0].values if 'stundenwerte' in c]

## ============================================================= ##
## DOWNLOAD AND PROCESS EACH STATION FILE
## ============================================================= ##
# Initialise an empty DataFrame to collect metadata for all stations.
# One row per station will be appended inside the loop below.
df_stations = pd.DataFrame()

for filename in filelist:
  print(filename)  # Progress indicator: print current filename to console

# --- Download the zip archive ---
# Construct the full local file path where the archive will be saved temporarily.
archivefile = os.path.join(DATAPATH_DWD_STATIONS, filename)

# Download the zip file from the DWD server to the local path.
# urlretrieve(url, local_path) saves the file directly to disk.
urllib.request.urlretrieve(base_url + filename, archivefile)

# Open the downloaded zip archive for reading.
archive = zipfile.ZipFile(archivefile, 'r')

## --------------------------------------------------------- ##
## EXTRACT AND SAVE HOURLY TEMPERATURE DATA
## --------------------------------------------------------- ##
# Find the data file inside the archive. DWD data files start with
# 'produkt_' and contain the actual hourly measurements.
# Each archive contains exactly one such file.
ifiles = [s for s in archive.namelist() if 'produkt_' in s]

# Open and read all lines of the data file.
# Lines are returned as bytes; str(l) converts each to a string for splitting.
ifp = archive.open(ifiles[0], "r")
lines = ifp.readlines()

# Parse the semicolon-delimited data file manually line by line.
# lines[0] is the header row — lines[1:] skips it to get data rows.
# Column positions (0-indexed after splitting by ';'):
#   [1] datetime   : timestamp in format YYYYMMDDHH
#   [2] QN_9       : quality control flag (Qualitätsniveau)
#   [3] TT_TU      : air temperature at 2 m height (°C)
#   [4] RF_TU      : relative humidity (%)
dfl = pd.DataFrame({'datetime': [str(l).split(';')[1].strip() for l in lines[1:]]})
dfl['TT_TU'] = [str(l).split(';')[3].strip() for l in lines[1:]]
dfl['RF_TU'] = [str(l).split(';')[4].strip() for l in lines[1:]]
dfl['QN_9'] = [str(l).split(';')[2].strip() for l in lines[1:]]

# Extract the 5-digit DWD station ID from the zip filename.
# DWD filenames follow the pattern: stundenwerte_TU_SSSSS_YYYYMMDD_YYYYMMDD_hist.zip
# where SSSSS is the station ID at position [2] after splitting by '_'.
station_id = filename.split('_')[2]

# Build the output filename using the station ID and the date range
# of the data (first and last timestamp in the file).
ofilename = 'dwd_cdc_hourly_air_temperature_TU_{0:s}_{1:s}-{2:s}.csv'.format(\
                                                                             station_id,
                                                                             dfl['datetime'].values[0], dfl['datetime'].values[-1])

# Save the parsed hourly temperature data to a CSV file.
# index=False omits the pandas row index from the output.
dfl.to_csv(os.path.join(DATAPATH_DWD_STATIONS, ofilename), index=False)

## --------------------------------------------------------- ##
## EXTRACT STATION METADATA (LOCATION AND NAME)
## --------------------------------------------------------- ##
# Find the station geography metadata file inside the archive.
# DWD archives include a 'Geographie' text file with station coordinates.
ifiles = [s for s in archive.namelist() if (('Geographie' in s) and ('txt' in s))]

# Open and read the geography file.
ifp = archive.open(ifiles[0], "r")
lines = ifp.readlines()

# The last line of the geography file contains the most recent station record.
# Fields are semicolon-separated in the order:
#   [0] station_id  (unused here, already extracted from filename)
#   [1] elevation   : station elevation in metres above sea level
#   [2] lat         : latitude in decimal degrees
#   [3] lon         : longitude in decimal degrees
#   [-1] name       : station name (last field, strip removes trailing whitespace
#                     and [:-3] removes the trailing '\r\n' bytes artefact)
newrow = pd.DataFrame({\
  'station':   station_id,
  'lon':       str(lines[-1]).split(';')[3].strip(),
  'lat':       str(lines[-1]).split(';')[2].strip(),
  'elevation': str(lines[-1]).split(';')[1].strip(),
  'name':      str(lines[-1]).split(';')[-1].strip()[:-3]}, index=[0])

# Append the new station row to the running metadata DataFrame.
# ignore_index=True re-numbers the index to avoid duplicate index values.
df_stations = pd.concat([df_stations, newrow], axis=0, ignore_index=True)

## --------------------------------------------------------- ##
## CLEAN UP
## --------------------------------------------------------- ##
# Close the zip archive handle to release the file lock.
archive.close()

# Delete the downloaded zip file to save disk space.
# The parsed CSV has already been saved above, so the archive is no longer needed.
os.remove(archivefile)

## ============================================================= ##
## SAVE STATION METADATA
## ============================================================= ##
# Write the complete station metadata table (one row per station,
# columns: station, lon, lat, elevation, name) to a CSV file.
# This file can later be loaded as a reference table or converted to
# a shapefile for spatial mapping (e.g. in the temperature difference script).
df_stations.to_csv(os.path.join(DATAPATH_DWD_STATIONS, 'stations.csv'), index=False)
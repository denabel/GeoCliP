#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pandas as pd
import zipfile
import urllib.request

## ============================================================================================= ##

DATAPATH_DWD_STATIONS = './'

## ============================================================================================= ##

base_url = 'https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/air_temperature/historical/'

filelist = pd.read_csv(base_url)
filelist = [c.split("href=")[1].split('>')[0][1:-1] for c in filelist.iloc[:, 0].values if 'stundenwerte' in c]

df_stations = pd.DataFrame()

for filename in filelist:

	print(filename)

	archivefile = os.path.join(DATAPATH_DWD_STATIONS, filename)
	urllib.request.urlretrieve(base_url + filename, archivefile)
	archive = zipfile.ZipFile(archivefile, 'r')
	ifiles = [s for s in archive.namelist() if 'produkt_' in s]
	ifp = archive.open(ifiles[0], "r") 
	lines = ifp.readlines()
	dfl = pd.DataFrame({'datetime': [str(l).split(';')[1].strip() for l in lines[1:]]})
	dfl['TT_TU'] = [str(l).split(';')[3].strip() for l in lines[1:]]
	dfl['RF_TU'] = [str(l).split(';')[4].strip() for l in lines[1:]]
	dfl['QN_9'] = [str(l).split(';')[2].strip() for l in lines[1:]]
	station_id = filename.split('_')[2]
	ofilename = 'dwd_cdc_hourly_air_temperature_TU_{0:s}_{1:s}-{2:s}.csv'.format(\
			station_id,
			dfl['datetime'].values[0], dfl['datetime'].values[-1])
	dfl.to_csv(os.path.join(DATAPATH_DWD_STATIONS, ofilename), index=False)

	ifiles = [s for s in archive.namelist() if (('Geographie' in s) and ('txt' in s))]
	ifp = archive.open(ifiles[0], "r") 
	lines = ifp.readlines()
	newrow = pd.DataFrame({\
			'station': station_id,
			'lon': str(lines[-1]).split(';')[3].strip(),
			'lat': str(lines[-1]).split(';')[2].strip(),
			'elevation': str(lines[-1]).split(';')[1].strip(),
			'name': str(lines[-1]).split(';')[-1].strip()[:-3]}, index=[0])
	df_stations = pd.concat([df_stations, newrow], axis=0, ignore_index=True)

	archive.close()
	os.remove(archivefile)

df_stations.to_csv(os.path.join(DATAPATH_DWD_STATIONS, 'stations.csv'), index=False)

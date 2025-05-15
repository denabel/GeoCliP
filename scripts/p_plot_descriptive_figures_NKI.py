#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import numpy as np
import pandas as pd

import datetime

import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns

import geopandas as gpd

## ============================================================= ##

DATAPATH = './'
FIGUREPATH = './'

## ============================================================= ##

df = pd.read_csv(os.path.join(DATAPATH, 'NKI_full_list_06122023.csv', sep=';', encoding='latin-1'))

datapath = os.path.join(DATAPATH, "vg5000_12-31.gk3.shape.ebenen/vg5000_ebenen_1231/")
datafile = "VG5000_GEM.shp"
gdf_districts = gpd.read_file(os.path.join(datapath, datafile))

## ============================================================= ##

df['date_start'] = df['="Laufzeit von"'].apply(lambda x: datetime.datetime.strptime(x[2:-1].strip(), '%d.%m.%Y'))
df['year_start'] = df['date_start'].apply(lambda x: int(x.year))

df['project_type'] = df['="Klartext Leistungsplansystematik"'].apply(lambda x: x[2:-1].strip().replace('KSI -', ''))

df['project_size'] = df['="Fördersumme in EUR"'].apply(lambda x: float(x.replace('.', '').replace(',', '.').strip())) / 1000.

df['district_code'] = df['="Gemeindekennziffer"'].apply(lambda x: x[2:-1].strip())

## ============================================================= ##

fig, ax = plt.subplots(figsize=(4,4))
sns.distplot(df['year_start'].values, bins=np.arange(2005, 2023, 1)-0.5)
ax.set_xlabel('First year of project')
ax.set_ylabel('Frequency')
ax.set_xticks(np.arange(2005, 2025+5, 5))
fig.savefig(os.path.join(FIGUREPATH, 'year_start.png'), bbox_inches='tight', dpi=400)

## ============================================================= ##

fig, ax = plt.subplots(figsize=(4,4))
sns.distplot(df['project_size'].values, bins=np.arange(0, 500+50, 50))
ax.set_xlabel('Size of project (k EUR)')
ax.set_ylabel('Frequency')
ax.set_xticks(np.arange(0, 500+50, 50))
ax.set_xlim(0., 500)
fig.savefig(os.path.join(FIGUREPATH, 'project_size.png'), bbox_inches='tight', dpi=400)

## ============================================================= ##

dfc = df.groupby('project_type')['year_start'].count().reset_index()

fig, ax = plt.subplots(figsize=(6,6))
sns.barplot(data=dfc, x='year_start', y='project_type')
ax.set_xlabel('Number of projects')
ax.set_ylabel('Type of project')
fig.savefig(os.path.join(FIGUREPATH, 'project_type.png'), bbox_inches='tight', dpi=400)

## ============================================================= ##

dfc = df.groupby('project_type')['project_size'].sum().reset_index()
dfc['project_size'] = dfc['project_size'] / 1e3

fig, ax = plt.subplots(figsize=(6,6))
sns.barplot(data=dfc, x='project_size', y='project_type') 
ax.set_xlabel('Total investments (mil EUR)')
ax.set_ylabel('Type of project')
fig.savefig(os.path.join(FIGUREPATH, 'project_type_investment.png'), bbox_inches='tight', dpi=400)

## ============================================================= ##

dfc = df.groupby('district_code')['year_start'].count().reset_index()

gdf = gdf_districts.merge(dfc, left_on='AGS_0', right_on='district_code', how='left')

cmap = plt.cm.Greens
bounds = np.arange(0, 50+5, 5)
norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
formatcode = '%.0f'

fig, ax = plt.subplots(figsize=(6,6))
ax2 = fig.add_axes([0.85, 0.2, 0.03, 0.6])
cb = mpl.colorbar.ColorbarBase(ax2, cmap=cmap, norm=norm,
				spacing='uniform', ticks=bounds, boundaries=bounds, format=formatcode,
				extend='max', orientation='vertical')
cb.ax.tick_params(labelsize='small')
cb.set_label(label="Number of projects", size='small')
ax.set_title(None)
gdf_districts.plot(ax=ax, alpha=1., facecolor='grey', lw=0.05, edgecolor='k')
gdf.plot(ax=ax, alpha=1., facecolor='#D3D3D3', lw=0., edgecolor='grey')
gdf.plot(ax=ax, alpha=1., column='year_start', lw=0., cmap=cmap, norm=norm, edgecolor='grey')
gdf_districts.plot(ax=ax, alpha=1., facecolor='none', lw=0.05, edgecolor='k')
ax.set_xlabel(None)
ax.set_ylabel(None)
ax.set_xticklabels([])
ax.set_yticklabels([])
fig.savefig(os.path.join(FIGUREPATH, 'map_projects.png'), bbox_inches='tight', dpi=400)


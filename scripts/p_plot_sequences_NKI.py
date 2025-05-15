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

def expand_df(df, dims, values):
	df = df.set_index(dims)
	multi_index = (pd.MultiIndex.from_product(
			iterables=values,
			names=dims))
	df = df.reindex(multi_index, fill_value=np.nan).reset_index()
	df = df.sort_values(by=dims, ascending=True).reset_index(drop=True)
	return df

def sequence(df_prob):
	cols = list(df_prob.columns)
	rows = list(df_prob.index)
	order = []
	for n in range(df_prob.shape[0]):
		counters = [0] * len(rows)
		for i, dim1 in enumerate(rows):
			for j, dim2 in enumerate([c for c in cols if c != dim1]):
				if ((dim1 in df_prob.index) and (dim2 in df_prob.columns) and 
					(dim1 in df_prob.columns) and (dim2 in df_prob.index)):
					if df_prob.loc[dim1, dim2] > df_prob.loc[dim2, dim1]:
						counters[i] += 1
		first = list(reversed([x for _, x in sorted(zip(counters, rows))]))[0]
		order.append(first)
		rows.remove(first)
	return order

policy2policy = {\
	'Erstellung von Klimaschutzkonzepten': "Climate strategy", 
	'Klimaschutzkonzepte und Klimaschutzmanagement': "Climate manager", 
	'Einführung Energiesparmodelle': "Energy-saving models", 
	'Energiemanagementsysteme': "Energy management",
	'Klimaschutz bei stillgelegten Siedlungsabfalldeponien': "Landfill sites", 
	'Investive Maßnahmen zur Förderung einer nachhaltigen Mobilität': "Sustainable mobility measures", 
	'Masterplan 100%': "Masterplan 100%", 
}

## ============================================================= ##

df = pd.read_csv(os.path.join(DATAPATH, 'NKI_full_list_06122023.csv'), sep=';', encoding='latin-1')

## ============================================================= ##

df['date_start'] = df['="Laufzeit von"'].apply(lambda x: datetime.datetime.strptime(x[2:-1].strip(), '%d.%m.%Y'))
df['year_start'] = df['date_start'].apply(lambda x: int(x.year))
df['project_type'] = df['="Klartext Leistungsplansystematik"'].apply(lambda x: x[2:-1].strip().replace('KSI -', '').strip())
df['project_size'] = df['="Fördersumme in EUR"'].apply(lambda x: float(x.replace('.', '').replace(',', '.').strip())) / 1000.
df['district_code'] = df['="Gemeindekennziffer"'].apply(lambda x: x[2:-1].strip())

## ============================================================= ##

df_first = df.groupby(['district_code', 'project_type'])['year_start'].min().reset_index()
policies = df_first['project_type'].unique()

## ============================================================= ##
## all policies
## ============================================================= ##

df_results = pd.DataFrame(columns=['policy_first', 'policy_second'])

for policy in policies:
	df1 = df_first.loc[df_first['project_type'] == policy, :]
	for other_policy in [p for p in policies if p != policy]:
		df2 = df_first.loc[df_first['project_type'] == other_policy, :]
		df_both = df1.merge(df2, on='district_code', how='outer')
		df_both['sequence'] = df_both['year_start_x'] < df_both['year_start_y']

		df_results = pd.concat([df_results,
			pd.DataFrame({'policy_first': policy, 'policy_second': other_policy,
							'freq': df_both['sequence'].sum() / df1.shape[0]}, index=[0])], axis=0)

## ============================================================= ##

df_prob = df_results.pivot_table(index=['policy_second'], columns=['policy_first'], values=['freq'])
df_prob = df_prob.T
df_prob.index = [s[1] for s in df_prob.index.values]
df_prob = df_prob * 100.
seq = sequence(df_prob)

## ============================================================= ##

df_prob = df_prob.loc[seq, seq]

xticklabels = df_prob.index.values
yticklabels = df_prob.columns.values

for i in range(len(yticklabels)):
	yticklabels[i] = yticklabels[i].strip() + ' [{0:d}]'.format(i)
xticklabels = [str(i) for i in range(len(xticklabels))]

fig, ax = plt.subplots()
ax.set_title('Conditional probability of observing B prior to A')
#sns.heatmap(df_prob, cmap='YlGn', annot=df_ann, linecolor='k', lw=0.5, ax=ax, fmt='s')
sns.heatmap(df_prob, cmap='YlGn', linecolor='k', lw=0.5, ax=ax, fmt='s')
sns.despine(ax=ax, offset=1., right=True, top=True)
#ax.set_yticklabels(instrumentnames)
#ax.set_xticklabels(sectornames)
ax.set_ylabel("Policy B in year t-1")
ax.set_xlabel('Policy A in year t')
ax.set_xticks(np.arange(len(xticklabels)) + 0.5)
ax.set_yticks(np.arange(len(yticklabels)) + 0.5)
ax.set_xticklabels(xticklabels, rotation=90)
ax.set_yticklabels(yticklabels)
fig.savefig(os.path.join(FIGUREPATH, 'heatmap_probabilities_sequences_all.png'), bbox_inches='tight', dpi=300.)

## ============================================================= ##
## most frequent policies
## ============================================================= ##

policies_frequent = df['project_type'].value_counts()
policies = policies_frequent[policies_frequent > 100.].index

df_results = pd.DataFrame(columns=['policy_first', 'policy_second'])

for policy in policies:
	df1 = df_first.loc[df_first['project_type'] == policy, :]
	for other_policy in [p for p in policies if p != policy]:
		df2 = df_first.loc[df_first['project_type'] == other_policy, :]
		df_both = df1.merge(df2, on='district_code', how='outer')
		df_both['sequence'] = df_both['year_start_x'] < df_both['year_start_y']

		df_results = pd.concat([df_results,
			pd.DataFrame({'policy_first': policy, 'policy_second': other_policy,
							'freq': df_both['sequence'].sum() / df1.shape[0]}, index=[0])], axis=0)

## ============================================================= ##

df_prob = df_results.pivot_table(index=['policy_second'], columns=['policy_first'], values=['freq'])
df_prob = df_prob.T
df_prob.index = [s[1] for s in df_prob.index.values]
df_prob = df_prob * 100.
seq = sequence(df_prob)

## ============================================================= ##

df_prob = df_prob.loc[seq, seq]

xticklabels = df_prob.index.values
yticklabels = df_prob.columns.values

for i in range(len(yticklabels)):
	yticklabels[i] = yticklabels[i].strip() + ' [{0:d}]'.format(i)
xticklabels = [str(i) for i in range(len(xticklabels))]

fig, ax = plt.subplots()
ax.set_title('Conditional probability of observing B prior to A')
#sns.heatmap(df_prob, cmap='YlGn', annot=df_ann, linecolor='k', lw=0.5, ax=ax, fmt='s')
sns.heatmap(df_prob, cmap='YlGn', linecolor='k', lw=0.5, ax=ax, fmt='s')
sns.despine(ax=ax, offset=1., right=True, top=True)
#ax.set_yticklabels(instrumentnames)
#ax.set_xticklabels(sectornames)
ax.set_ylabel("Policy B in year t-1")
ax.set_xlabel('Policy A in year t')
ax.set_xticks(np.arange(len(xticklabels)) + 0.5)
ax.set_yticks(np.arange(len(yticklabels)) + 0.5)
ax.set_xticklabels(xticklabels, rotation=90)
ax.set_yticklabels(yticklabels)
fig.savefig(os.path.join(FIGUREPATH, 'heatmap_probabilities_sequences_frequent.png'), bbox_inches='tight', dpi=300.)

## ============================================================= ##
## selected policies
## ============================================================= ##

policies_frequent = df['project_type'].value_counts()
policies = list(policy2policy.keys())

df_results = pd.DataFrame(columns=['policy_first', 'policy_second'])

for policy in policies:
	df1 = df_first.loc[df_first['project_type'] == policy, :]
	for other_policy in [p for p in policies if p != policy]:
		df2 = df_first.loc[df_first['project_type'] == other_policy, :]
		df_both = df1.merge(df2, on='district_code', how='outer')
		df_both['sequence'] = df_both['year_start_x'] < df_both['year_start_y']

		df_results = pd.concat([df_results,
			pd.DataFrame({'policy_first': policy, 'policy_second': other_policy,
							'freq': df_both['sequence'].sum() / df1.shape[0]}, index=[0])], axis=0)

## ============================================================= ##

df_prob = df_results.pivot_table(index=['policy_second'], columns=['policy_first'], values=['freq'])
df_prob = df_prob.T
df_prob.index = [s[1] for s in df_prob.index.values]
df_prob = df_prob * 100.
seq = sequence(df_prob)

## ============================================================= ##

df_prob = df_prob.loc[seq, seq]

xticklabels = df_prob.index.values
yticklabels = df_prob.columns.values

for i in range(len(yticklabels)):
	yticklabels[i] = policy2policy.get(yticklabels[i].strip(), yticklabels[i].strip())  + ' [{0:d}]'.format(i)
xticklabels = [str(i) for i in range(len(xticklabels))]

fig, ax = plt.subplots()
ax.set_title('Conditional probability of observing B prior to A')
#sns.heatmap(df_prob, cmap='YlGn', annot=df_ann, linecolor='k', lw=0.5, ax=ax, fmt='s')
sns.heatmap(df_prob, cmap='YlGn', linecolor='k', lw=0.5, ax=ax, fmt='s')
sns.despine(ax=ax, offset=1., right=True, top=True)
#ax.set_yticklabels(instrumentnames)
#ax.set_xticklabels(sectornames)
ax.set_ylabel("Policy B in year t-1")
ax.set_xlabel('Policy A in year t')
ax.set_xticks(np.arange(len(xticklabels)) + 0.5)
ax.set_yticks(np.arange(len(yticklabels)) + 0.5)
ax.set_xticklabels(xticklabels, rotation=90)
ax.set_yticklabels(yticklabels)
fig.savefig(os.path.join(FIGUREPATH, 'heatmap_probabilities_sequences_selected.png'), bbox_inches='tight', dpi=300.)


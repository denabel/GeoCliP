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
## ============================================================= ##
## STANDARD LIBRARY IMPORTS (no installation needed)
## ============================================================= ##
import os          # File path handling (os.path.join, os.path.exists, etc.)
import datetime    # Parsing and manipulating date/time objects

## ============================================================= ##
## THIRD-PARTY IMPORTS (require installation, see above)
## ============================================================= ##

# numpy: fundamental package for numerical computing in Python.
# Used here for array operations, bin edge construction (np.arange),
# and fill values (np.nan).
import numpy as np

# pandas: core library for tabular data manipulation.
# Used for loading CSVs, groupby aggregations, merges, and pivot tables.
import pandas as pd

# matplotlib: the base plotting library. pyplot provides a MATLAB-like
# interface for creating figures and axes. mpl (the top-level module)
# is imported separately to access lower-level objects like
# BoundaryNorm and ColorbarBase.
import matplotlib.pyplot as plt
import matplotlib as mpl

# seaborn: statistical visualisation library built on top of matplotlib.
# Provides higher-level plot types (distplot, barplot, heatmap) with
# better default aesthetics.
import seaborn as sns

# geopandas: extends pandas to support geographic/spatial data.
# Used here to load and plot the German municipal boundary shapefile.
# Note: geopandas depends on shapely, fiona, and pyproj — these are
# installed automatically via conda-forge or pip.
import geopandas as gpd

## ============================================================= ##
# Configuration: paths for input data and output figures
DATAPATH = './'
FIGUREPATH = './'

## ============================================================= ##
## HELPER FUNCTIONS
## ============================================================= ##

def expand_df(df, dims, values):
  
  #   Expand a DataFrame to include ALL combinations of the given dimensions,
  #   filling any missing combinations with NaN.
  # 
  #   This is useful when you have sparse data (not every combination of
  #   dimension values is observed) and you need a complete grid — for
  #   example, to later pivot into a full matrix without gaps.
  # 
  #   Parameters
  #   ----------
  #   df     : pd.DataFrame
  #       Input DataFrame containing at least the columns listed in `dims`.
  #   dims   : list of str
  #       Column names to use as the index dimensions for the expansion.
  #   values : list of iterables
  #       One iterable per dimension listing all desired values,
  #       e.g. [['A', 'B', 'C'], [2010, 2011, 2012]].
  # 
  #   Returns
  #   -------
  #   pd.DataFrame
  #       A new DataFrame with one row per combination of dimension values,
  #       sorted ascending by `dims`. Missing rows are filled with NaN.
  # 
  #   Example
  #   -------
  #   If dims=['policy', 'year'] and values=[['A','B'], [2010, 2011]],
  #   the result will have 4 rows: (A,2010), (A,2011), (B,2010), (B,2011).

    df = df.set_index(dims)
    # Build a MultiIndex covering every combination of the given value lists
    multi_index = pd.MultiIndex.from_product(iterables=values, names=dims)
    # Reindex to the full grid; rows not present in the original get NaN
    df = df.reindex(multi_index, fill_value=np.nan).reset_index()
    df = df.sort_values(by=dims, ascending=True).reset_index(drop=True)
    return df


def sequence(df_prob):
 
  #   Compute a dominance-based linear ordering of policies from a square
  #   pairwise probability matrix.
  # 
  #   The algorithm works as a repeated "tournament":
  #     1. For each remaining policy, count how many other remaining policies
  #        it beats (i.e. P(this policy precedes other) > P(other precedes this)).
  #     2. Place the policy with the most wins at the next position in the order.
  #     3. Remove it from the pool and repeat until all policies are placed.
  # 
  #   This produces an ordering where policies that tend to be adopted early
  #   appear first, and policies adopted late appear last — making the resulting
  #   heatmap easier to read along a temporal adoption sequence.
  # 
  #   Parameters
  #   ----------
  #   df_prob : pd.DataFrame
  #       Square DataFrame where df_prob.loc[A, B] is the probability (0–100)
  #       that policy A was adopted before policy B.
  #       Both rows and columns must be indexed by policy names.
  # 
  #   Returns
  #   -------
  #   order : list of str
  #       Policy names sorted from "most often adopted first" to
  #       "most often adopted last".
  
cols = list(df_prob.columns)
rows = list(df_prob.index)   # Remaining unplaced policies
order = []

for n in range(df_prob.shape[0]):
  # Initialise win counter for each remaining policy
  counters = [0] * len(rows)

for i, dim1 in enumerate(rows):
  # Compare dim1 against every other remaining policy
  for j, dim2 in enumerate([c for c in cols if c != dim1]):
  # Guard: both directions must exist in the matrix
  if ((dim1 in df_prob.index) and (dim2 in df_prob.columns) and
      (dim1 in df_prob.columns) and (dim2 in df_prob.index)):
  # dim1 'wins' this matchup if it preceded dim2 more often
  if df_prob.loc[dim1, dim2] > df_prob.loc[dim2, dim1]:
  counters[i] += 1

# Pick the policy with the highest win count; sort ascending and take last
first = list(reversed([x for _, x in sorted(zip(counters, rows))]))[0]
order.append(first)
rows.remove(first)   # Remove from pool before next round

return order


## ============================================================= ##
## POLICY LABEL MAPPING
## ============================================================= ##
# Maps full German policy names (as they appear in the raw data) to
# short English labels used in the axis tick labels of the "selected
# policies" heatmap. Add or remove entries here to change which
# policies are included in that analysis.
policy2policy = {
  'Erstellung von Klimaschutzkonzepten':                              "Climate strategy",
  'Klimaschutzkonzepte und Klimaschutzmanagement':                    "Climate manager",
  'Einführung Energiesparmodelle':                                    "Energy-saving models",
  'Energiemanagementsysteme':                                         "Energy management",
  'Klimaschutz bei stillgelegten Siedlungsabfalldeponien':            "Landfill sites",
  'Investive Maßnahmen zur Förderung einer nachhaltigen Mobilität':   "Sustainable mobility measures",
  'Masterplan 100%':                                                  "Masterplan 100%",
}

## ============================================================= ##
## DATA LOADING
## ============================================================= ##
# Load the NKI (National Climate Initiative / Nationale Klimaschutzinitiative)
# project list from a semicolon-delimited CSV file.
#
# sep=';'              : German CSV exports typically use ';' as the delimiter
#                        instead of ',' because ',' is used as the decimal separator.
# encoding='latin-1'  : Required for files containing German special characters
#                        (ä, ö, ü, ß). Use 'utf-8' if this raises a UnicodeDecodeError.
df = pd.read_csv(os.path.join(DATAPATH, 'NKI_full_list_06122023.csv'), sep=';', encoding='latin-1')

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
  lambda x: x[2:-1].strip().replace('KSI -', '').strip()
)

# Parse the funding amount from a German-formatted number string:
#   .replace('.', '')    : remove thousands separators (e.g. "1.234.567" → "1234567")
#   .replace(',', '.')   : replace decimal comma with decimal point ("1234,56" → "1234.56")
# Then divide by 1000 to convert from EUR to kEUR (thousands of EUR).
df['project_size'] = df['="Fördersumme in EUR"'].apply(
  lambda x: float(x.replace('.', '').replace(',', '.').strip())
) / 1000.

# Extract the Gemeindekennziffer (AGS — Amtlicher Gemeindeschlüssel),
# the official 8-digit German municipal district code, for merging with
# the shapefile later.
df['district_code'] = df['="Gemeindekennziffer"'].apply(lambda x: x[2:-1].strip())

## ============================================================= ##
## FIRST ADOPTION YEAR PER DISTRICT AND POLICY
## ============================================================= ##
# For the sequencing analysis we only care about *when* each district
# first adopted each policy type — repeated projects of the same type
# in the same district are ignored.
# groupby + min gives the earliest year_start per (district, policy) pair.
df_first = df.groupby(['district_code', 'project_type'])['year_start'].min().reset_index()

# Unique list of all policy types present in the data
policies = df_first['project_type'].unique()

## ============================================================= ##
## ANALYSIS 1: ALL POLICY TYPES
## ============================================================= ##
# Compute pairwise sequencing probabilities across ALL policy types in the data.
#
# For each ordered pair (policy A, policy B) we calculate:
#   freq = (number of districts where A was first adopted before B)
#          / (total number of districts that ever adopted A)
#
# This gives P(A precedes B | district adopted A), i.e. the conditional
# probability that A came first given that A was adopted at all.

df_results = pd.DataFrame(columns=['policy_first', 'policy_second'])

for policy in policies:
  # All districts that adopted this policy, with their first adoption year
  df1 = df_first.loc[df_first['project_type'] == policy, :]

for other_policy in [p for p in policies if p != policy]:
  # All districts that adopted the comparison policy
  df2 = df_first.loc[df_first['project_type'] == other_policy, :]

# Outer join on district_code so we keep all districts that adopted
# either policy. year_start_x = first year of `policy`,
# year_start_y = first year of `other_policy`.
df_both = df1.merge(df2, on='district_code', how='outer')

# Boolean: True where policy was adopted strictly before other_policy
df_both['sequence'] = df_both['year_start_x'] < df_both['year_start_y']

# Append result: freq is the share of policy-A districts where A came first
df_results = pd.concat([df_results,
                        pd.DataFrame({
                          'policy_first':  policy,
                          'policy_second': other_policy,
                          'freq': df_both['sequence'].sum() / df1.shape[0]
                        }, index=[0])], axis=0)

## ============================================================= ##
# Reshape the long-format results table into a square probability matrix.
#
# pivot_table: rows = policy_second, columns = policy_first, values = freq
# .T          : transpose so rows = policy_first, columns = policy_second
#               (i.e. entry [A, B] = P(A precedes B))
# * 100       : convert proportion (0–1) to percentage (0–100)
# sequence()  : compute the dominance-based row/column ordering
df_prob = df_results.pivot_table(index=['policy_second'], columns=['policy_first'], values=['freq'])
df_prob = df_prob.T
df_prob.index = [s[1] for s in df_prob.index.values]  # Flatten MultiIndex → policy name strings
df_prob = df_prob * 100.
seq = sequence(df_prob)

## ============================================================= ##
# Reorder both rows and columns by the dominance sequence so the
# heatmap flows from "earliest adopters" (top-left) to "latest" (bottom-right).
df_prob = df_prob.loc[seq, seq]

xticklabels = df_prob.index.values   # Numeric labels [0, 1, 2, ...] for x-axis
yticklabels = df_prob.columns.values # Full names with index suffix for y-axis

# Y-axis: append [i] to each label so the reader can match it to the x-axis number
for i in range(len(yticklabels)):
  yticklabels[i] = yticklabels[i].strip() + ' [{0:d}]'.format(i)
# X-axis: just use the numeric index to keep the axis readable
xticklabels = [str(i) for i in range(len(xticklabels))]

# Plot: YlGn colour scale — brighter green = higher probability that
# column policy (A) was adopted before row policy (B).
fig, ax = plt.subplots()
ax.set_title('Conditional probability of observing B prior to A')
sns.heatmap(df_prob, cmap='YlGn', linecolor='k', lw=0.5, ax=ax, fmt='s')
sns.despine(ax=ax, offset=1., right=True, top=True)
ax.set_ylabel("Policy B in year t-1")
ax.set_xlabel('Policy A in year t')
ax.set_xticks(np.arange(len(xticklabels)) + 0.5)  # Centre ticks in each cell
ax.set_yticks(np.arange(len(yticklabels)) + 0.5)
ax.set_xticklabels(xticklabels, rotation=90)
ax.set_yticklabels(yticklabels)
fig.savefig(os.path.join(FIGUREPATH, 'heatmap_probabilities_sequences_all.png'), bbox_inches='tight', dpi=300.)

## ============================================================= ##
## ANALYSIS 2: MOST FREQUENT POLICY TYPES ONLY
## ============================================================= ##
# Restrict the analysis to policies adopted by more than 100 districts.
# Rare policies (≤ 100 adopters) are excluded because their pairwise
# probability estimates would be based on very few observations and
# therefore unreliable.
policies_frequent = df['project_type'].value_counts()
policies = policies_frequent[policies_frequent > 100.].index

# --- Same pairwise sequencing loop as Analysis 1 ---
df_results = pd.DataFrame(columns=['policy_first', 'policy_second'])

for policy in policies:
  df1 = df_first.loc[df_first['project_type'] == policy, :]
for other_policy in [p for p in policies if p != policy]:
  df2 = df_first.loc[df_first['project_type'] == other_policy, :]
df_both = df1.merge(df2, on='district_code', how='outer')
df_both['sequence'] = df_both['year_start_x'] < df_both['year_start_y']
df_results = pd.concat([df_results,
                        pd.DataFrame({
                          'policy_first':  policy,
                          'policy_second': other_policy,
                          'freq': df_both['sequence'].sum() / df1.shape[0]
                        }, index=[0])], axis=0)

# --- Same reshape, sort, and plot pipeline as Analysis 1 ---
df_prob = df_results.pivot_table(index=['policy_second'], columns=['policy_first'], values=['freq'])
df_prob = df_prob.T
df_prob.index = [s[1] for s in df_prob.index.values]
df_prob = df_prob * 100.
seq = sequence(df_prob)

df_prob = df_prob.loc[seq, seq]
xticklabels = df_prob.index.values
yticklabels = df_prob.columns.values

for i in range(len(yticklabels)):
  yticklabels[i] = yticklabels[i].strip() + ' [{0:d}]'.format(i)
xticklabels = [str(i) for i in range(len(xticklabels))]

fig, ax = plt.subplots()
ax.set_title('Conditional probability of observing B prior to A')
sns.heatmap(df_prob, cmap='YlGn', linecolor='k', lw=0.5, ax=ax, fmt='s')
sns.despine(ax=ax, offset=1., right=True, top=True)
ax.set_ylabel("Policy B in year t-1")
ax.set_xlabel('Policy A in year t')
ax.set_xticks(np.arange(len(xticklabels)) + 0.5)
ax.set_yticks(np.arange(len(yticklabels)) + 0.5)
ax.set_xticklabels(xticklabels, rotation=90)
ax.set_yticklabels(yticklabels)
fig.savefig(os.path.join(FIGUREPATH, 'heatmap_probabilities_sequences_frequent.png'), bbox_inches='tight', dpi=300.)

## ============================================================= ##
## ANALYSIS 3: SELECTED / HAND-PICKED POLICY TYPES
## ============================================================= ##
# Repeat the analysis for the 7 specific policies defined in policy2policy.
# This allows a focused comparison of theoretically relevant policy types
# regardless of how frequently they appear in the data.
#
# Note: policies_frequent is recomputed here but not actually used —
# the policy list comes directly from policy2policy.keys().
policies_frequent = df['project_type'].value_counts()
policies = list(policy2policy.keys())

# --- Same pairwise sequencing loop as Analyses 1 & 2 ---
df_results = pd.DataFrame(columns=['policy_first', 'policy_second'])

for policy in policies:
  df1 = df_first.loc[df_first['project_type'] == policy, :]
for other_policy in [p for p in policies if p != policy]:
  df2 = df_first.loc[df_first['project_type'] == other_policy, :]
df_both = df1.merge(df2, on='district_code', how='outer')
df_both['sequence'] = df_both['year_start_x'] < df_both['year_start_y']
df_results = pd.concat([df_results,
                        pd.DataFrame({
                          'policy_first':  policy,
                          'policy_second': other_policy,
                          'freq': df_both['sequence'].sum() / df1.shape[0]
                        }, index=[0])], axis=0)

# --- Same reshape and sort pipeline ---
df_prob = df_results.pivot_table(index=['policy_second'], columns=['policy_first'], values=['freq'])
df_prob = df_prob.T
df_prob.index = [s[1] for s in df_prob.index.values]
df_prob = df_prob * 100.
seq = sequence(df_prob)

df_prob = df_prob.loc[seq, seq]
xticklabels = df_prob.index.values
yticklabels = df_prob.columns.values

# Replace full German names with short English labels from policy2policy.
# .get(key, default) falls back to the original name if no mapping exists.
for i in range(len(yticklabels)):
  yticklabels[i] = policy2policy.get(yticklabels[i].strip(), yticklabels[i].strip()) + ' [{0:d}]'.format(i)
xticklabels = [str(i) for i in range(len(xticklabels))]

fig, ax = plt.subplots()
ax.set_title('Conditional probability of observing B prior to A')
sns.heatmap(df_prob, cmap='YlGn', linecolor='k', lw=0.5, ax=ax, fmt='s')
sns.despine(ax=ax, offset=1., right=True, top=True)
ax.set_ylabel("Policy B in year t-1")
ax.set_xlabel('Policy A in year t')
ax.set_xticks(np.arange(len(xticklabels)) + 0.5)
ax.set_yticks(np.arange(len(yticklabels)) + 0.5)
ax.set_xticklabels(xticklabels, rotation=90)
ax.set_yticklabels(yticklabels)
fig.savefig(os.path.join(FIGUREPATH, 'heatmap_probabilities_sequences_selected.png'), bbox_inches='tight', dpi=300.)

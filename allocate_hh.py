#Copyright [2022] [Puget Sound Regional Council]

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import os
import shutil
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely import wkt
from shapely.geometry import Point
import sys
import yaml
import subprocess
import h5py
from pathlib import Path

# Copy user inputs to and set up populationsim directory
config = yaml.safe_load(open("config.yaml"))
popsim_run_dir_path = Path(config['popsim_run_dir'])
shutil.copyfile('populationsim_settings.yaml', popsim_run_dir_path/'configs'/'settings.yaml')
shutil.copyfile('controls.csv', popsim_run_dir_path/'configs'/'controls.csv')

# Set up other paths
land_use_path = Path(config['input_land_use_path'])
#if not os.path.isdir(r'PopulationSim/output'):
#    os.mkdir(r'PopulationSim/output')

# Run populationsim with controls for study area
returncode = subprocess.call([sys.executable, 'run_populationsim.py', '-w', config['popsim_run_dir']])
if returncode != 0:
    sys.exit(1)

#config = yaml.safe_load(open("config.yaml"))
soundcast_inputs_dir = 'results'

# Load data
parcels = pd.read_csv(land_use_path/'parcels_urbansim.txt', delim_whitespace=True)
synth_hhs = pd.read_csv(popsim_run_dir_path/'output'/'synthetic_households.csv')
synth_persons = pd.read_csv(popsim_run_dir_path/'output'/'synthetic_persons.csv')

# Load persons and households table from model run
# This file will be modified/replaced by new results from synthetic households 
myh5 = h5py.File(land_use_path/'hh_and_persons.h5','r')
old_h5_hh = pd.DataFrame()
for col in myh5['Household'].keys():
    old_h5_hh[col] = myh5['Household'][col][:]

old_h5_person = pd.DataFrame()
for col in myh5['Person'].keys():
    old_h5_person[col] = myh5['Person'][col][:]

# Households from the newly generated synthetic household file are allocated to parcels
# based on existing household distributions with TAZs. Parcels with more households are more likely
# to recieve new households (within a TAZ).
df_list = []
for taz in synth_hhs['taz_id'].unique():
    # Select all of the newly generated synthetic households assigned to a TAZ
    taz_df = synth_hhs[synth_hhs['taz_id']==taz][['taz_id', 'hh_id', 'household_id']]
    taz_parcels = parcels.loc[parcels['taz_p']==taz]
    if taz_parcels['hh_p'].sum()==0:
        # if no exisiting HHs in TAZ, assign uniform distribution; one hh for each parcel
        taz_parcels['hh_p'] = 1
    # Select all parcels in the TAZ with households 
    taz_parcels = taz_parcels[taz_parcels['hh_p']>0][['taz_p', 'hh_p', 'parcelid']]
    # Create records for each household and parcel
    taz_parcels = taz_parcels.loc[taz_parcels.index.repeat(taz_parcels['hh_p'])]
    # Return a random sample from the parcels equal to the original number of households in the taz
    taz_parcels = taz_parcels.sample(len(taz_df), replace = True)
    # merge HHs and their new parcels
    taz_parcels.reset_index(inplace=True)
    taz_df.reset_index(inplace=True)
    taz_df = taz_df.merge(taz_parcels, how='left', left_index=True, right_index=True)
    df_list.append(taz_df)

hh_parcels_df = pd.concat(df_list)
new_parcel_hhs_total = hh_parcels_df['parcelid'].value_counts()

#############################
# Update Parcel file
#############################
new_parcel_df = parcels.copy()
df = pd.DataFrame(new_parcel_hhs_total, columns=['new_hh'])
df.index.name = 'parcelid'
new_parcel_df = new_parcel_df.merge(df, left_on='parcelid', right_index=True, how='left')
new_parcel_df['hh_p'] = new_parcel_df['new_hh'].fillna(new_parcel_df['hh_p'])
new_parcel_df.drop('new_hh', axis=1, inplace=True)

# Update employment
if config['update_jobs']:
    df_allocate = pd.read_csv(popsim_run_dir_path/'allocation.csv')
    df_list = []
    for taz in df_allocate['zone_id'].unique():
        # Select all parcels in the zones
        df = new_parcel_df[new_parcel_df['taz_p'] == taz]

        # Scale the jobs based on existing distribution across sectors
        new_total = df_allocate[df_allocate['zone_id'] == taz]['employment']
        emp_factor = (new_total/df['emptot_p'].sum()).values[0]
        emp_cols = ['empedu_p', 'empfoo_p', 'empgov_p', 'empind_p', 'empmed_p','empofc_p', 'empoth_p', 'empret_p', 'emprsc_p', 'empsvc_p']
        new_parcel_df.loc[df.index, emp_cols] = (df[emp_cols]*emp_factor).round()
        # Note: the exact totals will not perfectly match the emptot_p specified, but will be generally close

# Update parcel columns with these new totals
new_parcel_df['emptot_p'] = new_parcel_df[emp_cols].sum(axis=1)

if not os.path.exists(soundcast_inputs_dir):
    os.mkdir(soundcast_inputs_dir)
new_parcel_df.to_csv(os.path.join(soundcast_inputs_dir,'parcels_urbansim.txt'), sep=' ', index=False)

#############################
# Update Household attributes
#############################
# See this link for converting to DaySim foramt http://twiki/Data/ParcelizingHouseholds
# Merge synthetic household data to newly parcelized houeshold data 
# Reformat to add as H5 info for household and persons
df_hh = hh_parcels_df.merge(synth_hhs, on='household_id', how='left')

df_hh = df_hh.rename(columns={'parcelid': 'hhparcel','taz_p': 'hhtaz', 
                        'NP': 'hhsize', 'HINCP': 'hhincome'})

# Set new household ID starting from highest value in existing H5
df_hh['hhno'] = range(old_h5_hh['hhno'].max()+1, old_h5_hh['hhno'].max()+len(df_hh)+1)

# Own/rent assigned based on seed household tenure data
hownrent_map = {
    1: 1,    # owned with mortage -> owned
    2: 1,    # owned free and clear -> owned
    3: 2,    # rented
    4: 3    # occupied without paying rent -> other
    }
df_hh['hownrent'] = df_hh['TEN'].map(hownrent_map)

# Housing type assumed based on share of single-family versus multifamily
# This field is unused in Daysim; this should be improved if this variable is ever used in the models
df_hh = df_hh.merge(parcels[['parcelid','sfunits','mfunits']], left_on='hhparcel', right_on='parcelid')
df_hh['hrestype'] = 1    # Default of single family residence
df_hh.loc[df_hh['mfunits'] > df_hh['sfunits'],'hrestype'] = 3    # condo/apartment

df_hh['hhexpfac'] = 1.0

########################
# Update person attributes
########################

# Relate PUMS attributes to Daysim variables

# columns required: pagey, pgend, pno, pptyp, pwtyp, pstyp
empty_fields = ['pdairy','ppaidprk','pspcl','pstaz','ptpass','puwarrp',
                'puwdepp','puwmode','pwpcl','pwtaz']
new_person_df = synth_persons.copy()

# Set empty fields to -1 and psexpfac to 1.0
new_person_df[empty_fields] = -1
new_person_df['psexpfac'] = 1.0

# These columns can be directly translated
new_person_df.rename(columns={'AGEP': 'pagey',    # integer age value
                               'SEX': 'pgend',    # gender 1: male, 2: female
                               'per_num': 'pno'    # person number within household
                               }, inplace=True)

# Worker type
# Get worker type based on usual hours worker per week (WKHP from PUMS)
# Assume less than 35 as part-time 
new_person_df.loc[new_person_df['WKHP'] == 0, 'pwtyp'] = 0    # not a worker
new_person_df.loc[new_person_df['WKHP'] >= 35 ,'pwtyp'] = 1    # full-time worker
new_person_df.loc[(new_person_df['WKHP'] < 35) & (new_person_df['WKHP'] > 0) ,'pwtyp'] = 2    # part-time worker

# Student type
new_person_df.loc[new_person_df['SCH'] == 1, 'pstyp'] = 0    # Not a student
new_person_df.loc[((new_person_df['SCH'] > 1) & (new_person_df['pwtyp'].isin([0,2]))), 'pstyp'] = 1    # student & not a full-time worker -> full-time student
new_person_df.loc[((new_person_df['SCH'] > 1) & (new_person_df['pwtyp'] == 1)), 'pstyp'] = 2    # student & full-time job -> part-time student

# Person type, based on employment, age, school status
new_person_df.loc[new_person_df['pwtyp'] == 1, 'pptyp'] = 1    # Full time worker
new_person_df.loc[new_person_df['pwtyp'] == 2, 'pptyp'] = 2    # Part time worker
new_person_df.loc[(new_person_df['pwtyp'] == 0) & (new_person_df['pagey'] >= 65), 'pptyp'] = 3    # Non working adult age 65+
new_person_df.loc[(new_person_df['pwtyp'] == 0) & (new_person_df['pagey'] < 65), 'pptyp'] = 4    # Non working adult age<65
new_person_df.loc[(new_person_df['pstyp'] > 0) & (new_person_df['SCHG'].isin([15,16])), 'pptyp'] = 5    # University student
new_person_df.loc[(new_person_df['pstyp'] > 0) & 
                  (new_person_df['SCHG'].isin([11,12,13,14]) &
                  (new_person_df['pagey'] >= 16)), 'pptyp'] = 6     # High school student age 16+
new_person_df.loc[(new_person_df['pagey'] >= 5) & (new_person_df['pagey'] < 16), 'pptyp'] = 7     # Child age 5-15
new_person_df.loc[(new_person_df['pagey'] < 5) & (new_person_df['pagey'] < 16), 'pptyp'] = 8    # Child age 0-4

# Get associated household ID
new_person_df = new_person_df.merge(df_hh[['household_id','hhno']], on='household_id', how='left')

####################
# Write results to H5
####################
# 
# Remove all households/persons from affected areas and replace with 
# newly synthesized data
export_hh_df = old_h5_hh[~old_h5_hh['hhtaz'].isin(df_hh['hhtaz'])]
df_hh[['hrestype','hownrent']] = -1
export_hh_df = export_hh_df.append(df_hh[export_hh_df.columns])

# Select persons from households within the final export list
export_person_df = old_h5_person[old_h5_person['hhno'].isin(export_hh_df['hhno'])]
export_person_df = export_person_df.append(new_person_df[old_h5_person.columns])

# Write to h5 file
out_h5 = h5py.File(popsim_run_dir_path/'output'/'hh_and_persons.h5','w')
for key in ['Person','Household']:
    out_h5.create_group(key)
for col in export_person_df.columns:
    out_h5['Person'][col] = export_person_df[col]
for col in export_hh_df.columns:
    out_h5['Household'][col] = export_hh_df[col]

out_h5.close()
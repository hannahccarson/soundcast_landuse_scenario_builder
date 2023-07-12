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

os.chdir(r'C:\Users\hannah.carson\OneDrive - Resource Systems Group, Inc\PierceCounty\psrc_landuse_allocator\Task_landuse_allocator')
# Copy user inputs to and set up populationsim directory
config = yaml.safe_load(open("config.yaml"))
popsim_run_dir_path = Path(config['output_dir'])
shutil.copyfile('populationsim_settings.yaml', popsim_run_dir_path/'configs'/'settings.yaml')
#shutil.copyfile('populationsim_settings_mp.yaml', popsim_run_dir_path/'configs'/'settings_mp.yaml')
shutil.copyfile('controls.csv', popsim_run_dir_path/'configs'/'controls.csv')

# Set up other paths
land_use_path = Path(config['input_land_use_path'])

if not config['allocation_only']:
    # Update controls from allocation file before running popsim:
    if config['update_hh'] or config['update_person']:
        df_allocate = pd.read_csv(popsim_run_dir_path/'data'/'user_allocation.csv')
        df = pd.read_csv(popsim_run_dir_path/'data'/'future_controls.csv')
        col_list = ['taz_id']
        if config['update_hh']:
            col_list += ['households']
        if config['update_persons']:
            col_list += ['persons']

        df = df_allocate[col_list].merge(df, how='left', on='taz_id')   # Join only zones from user_allocation.csv

        # for zones without existing distributions and user-specified targets, use regional averages
        update_tazs = df['taz_id']
        
        # Use average household size of 2.0 if number of persons not specified in user_allocation.csv
        df.loc[(df['taz_id'].isin(update_tazs)) &(df['persons'] == 0), 'persons'] = df['households']*2.0

        # regional household totals for control calculations
        tot_hh = df.loc[df['taz_id'].isin(update_tazs), 'hh_taz_weight'].sum()
        tot_person = df.loc[df['taz_id'].isin(update_tazs), 'pers_taz_weight'].sum()

        for col in config['household_cols']:
            print(col, tot_hh, df[col].sum()/tot_hh)
            df.loc[df['taz_id'].isin(update_tazs), col] = (df['households']*(df[col].sum()/tot_hh)).astype('int')
        for col in config['person_cols']:
            print(col)
            df.loc[df['taz_id'].isin(update_tazs), col] = (df['persons']*(df[col].sum()/tot_person)).astype('int')

        if config['update_hh']:
            df['hh_taz_weight'] = df['households'].copy()
            df.drop(['households'], axis=1, inplace=True)
        if config['update_persons']:
            df['pers_taz_weight'] = df['persons'].copy()
            df.drop(['persons'], axis=1, inplace=True)

        ## Enforce integers
        df.fillna(0, inplace = True)
        df = df.astype('int')
        df.to_csv(popsim_run_dir_path/'data'/'future_controls.csv', index=False)

    # Run populationsim with controls for study area
    returncode = subprocess.call([sys.executable, 'run_populationsim.py', '-w', config['output_dir']])
    if returncode != 0:
        sys.exit(1)

# Load data
parcels = pd.read_csv(land_use_path/'parcels_urbansim.txt', delim_whitespace=True)
parcels.columns = [col.lower() for col in parcels.columns]
synth_hhs = pd.read_csv(popsim_run_dir_path/'output'/'synthetic_households.csv')
synth_persons = pd.read_csv(popsim_run_dir_path/'output'/'synthetic_persons.csv')
manual_override = False
if config['allocation_override'] is not None:
    override = pd.read_csv(popsim_run_dir_path/'..'/config['allocation_override'])
    override = override.merge(parcels[['parcelid','taz_p']], how = 'left', on = 'parcelid')
    manual_override = True
if config['parcel_weights'] is not None:
    pcl_wgt = pd.read_csv(popsim_run_dir_path/'..'/config['parcel_weights'])
    pcl_wgt['weight'] = pcl_wgt['weight']
    parcels = parcels.merge(pcl_wgt, how = 'left', on = 'parcelid')
    parcels = parcels.fillna(0)
    parcels['hh_p'] = parcels['hh_p']*(parcels['weight']+1)
    parcels['hh_p'] = parcels['hh_p'].apply(round)
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
    if manual_override:
        for parcel in override[override.taz_p == taz].parcelid.unique():
            parcel_override = taz_df.sample(override.loc[override['parcelid'] == parcel].hh_p.item())
            parcel_override['parcelid'] = parcel
            parcel_override['taz_p'] = taz
            df_list.append(parcel_override)
            taz_df = taz_df[~(taz_df.household_id.isin(parcel_override.household_id.unique()))]
            taz_parcels = taz_parcels[~(taz_parcels.parcelid == parcel)]
            
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
df = pd.DataFrame(new_parcel_hhs_total)
df.columns = ['new_hh']
df.index.name = 'parcelid'
new_parcel_df = new_parcel_df.merge(df, left_on='parcelid', right_index=True, how='left')
# new_parcel_df['hh_p'] = new_parcel_df['new_hh'].fillna(new_parcel_df['hh_p'])
new_parcel_df['hh_p'] = new_parcel_df['new_hh'].fillna(0)
new_parcel_df.drop('new_hh', axis=1, inplace=True)

# Update employment
if config['update_jobs']:
    df_allocate = pd.read_csv(popsim_run_dir_path/'data'/'user_allocation.csv')
    df_allocate = df_allocate[df_allocate['employment'] > 0]
    emp_cols = ['empedu_p', 'empfoo_p', 'empgov_p', 'empind_p', 'empmed_p','empofc_p', 'empoth_p', 'empret_p', 'emprsc_p', 'empsvc_p']
    df_list = []
    for taz in df_allocate['taz_id'].unique():
        # Select all parcels in the zones
        df = new_parcel_df[new_parcel_df['taz_p'] == taz]

        if df['emptot_p'].sum() > 0:
            # For zones with existing distribution, scale jobs based on existing distribution across sectors
            new_total = df_allocate[df_allocate['taz_id'] == taz]['employment']
            emp_factor = (new_total/df['emptot_p'].sum()).values[0]
            new_parcel_df.loc[df.index, emp_cols] = (df[emp_cols]*emp_factor).round()
            # Note: due to rounding the exact totals will not perfectly match the emptot_p specified, but will be close
        else:
            # For zones without any distribution scale jobs across sectors using regional distributions
            # Use an even distribution across all parcels
            new_total = df_allocate[df_allocate['taz_id'] == taz]['employment']

            # Iterate through each parcel and sector and assign jobs as uniformly as possible
            emp_factor = (new_total/new_parcel_df['emptot_p'].sum()).values[0]
            # FIXME: iterating is slow, but we should only have to use it sparingly since most controls should already work off existing job distributions
            for col in emp_cols:
                new_parcel_df[col].fillna(0, inplace=True)
                # total jobs by sector
                jobs_to_assign = (new_total*(new_parcel_df[col].sum()/new_parcel_df['emptot_p'].sum())).round().astype('int').values[0]
                while jobs_to_assign > 0:
                    if jobs_to_assign <= len(new_parcel_df.loc[new_parcel_df['taz_p'] == taz]):
                        # Fewer or equal jobs than parcels in zone; assign jobs to the first parcels in the df
                        new_parcel_df.loc[new_parcel_df[new_parcel_df['taz_p'] == taz][0:jobs_to_assign].index, col] = new_parcel_df[col] + 1
                        jobs_to_assign = 0
                    else:
                        # More jobs than parcels; iterate until all sector jobs are placed
                        new_parcel_df.loc[new_parcel_df['taz_p'] == taz, col] = new_parcel_df[col] + 1
                        jobs_to_assign = jobs_to_assign - new_parcel_df.loc[new_parcel_df['taz_p'] == taz, col].sum().astype('int')


# Update parcel columns with these new totals
new_parcel_df['emptot_p'] = new_parcel_df[emp_cols].sum(axis=1)
new_parcel_df[emp_cols] = new_parcel_df[emp_cols].fillna(0)

# Integerize all cols
int_cols = new_parcel_df.columns.drop(['xcoord_p','ycoord_p'])
new_parcel_df[int_cols] = new_parcel_df[int_cols].astype('int')

new_parcel_df.to_csv(popsim_run_dir_path/'output'/'parcels_urbansim.txt', sep=' ', index=False)

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

df_hh['hhexpfac'] = 1
df_hh[['hrestype','hownrent']] = -1

########################
# Update person attributes
########################

# Relate PUMS attributes to Daysim variables

# columns required: pagey, pgend, pno, pptyp, pwtyp, pstyp
empty_fields = ['pdairy','ppaidprk','pspcl','pstaz','ptpass','puwarrp',
                'puwdepp','puwmode','pwpcl','pwtaz','prace']
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
# If no SCH information, set to 0 (not a student); this occurs for people of pagey 0-2
new_person_df.loc[new_person_df['SCH'] == 0, 'pstyp'] = 0

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

# Race
# white_non_hispanic 
new_person_df.loc[(new_person_df.RAC1P == 1) & (new_person_df.HISP<2), 'prace'] = 1
# black_non_hispanic
new_person_df.loc[(new_person_df.RAC1P == 2) & (new_person_df.HISP<2), 'prace'] = 2
# asian_non_hispanic
new_person_df.loc[(new_person_df.RAC1P==6) & (new_person_df.HISP<2), 'prace'] = 3
# other_non_hispanic
new_person_df.loc[(new_person_df.RAC1P != 1) & (new_person_df.RAC1P != 2) & (new_person_df.RAC1P != 6) & (new_person_df.RAC1P != 9) & (new_person_df.HISP<2), 'prace'] = 4
# two_or_more_races_non_hispanic
new_person_df.loc[(new_person_df.RAC1P==9) & (new_person_df.HISP<2), 'prace'] = 5
# white_hispanic
new_person_df.loc[(new_person_df.RAC1P == 1) & (new_person_df.HISP>1), 'prace'] = 6
# non_white_hispanic
new_person_df.loc[(new_person_df.RAC1P != 1) & (new_person_df.HISP>1), 'prace'] = 7

# Get associated household ID
new_person_df = new_person_df.merge(df_hh[['household_id','hhno']], on='household_id', how='left')

####################
# Write results to H5
####################

# When working with a small study area, only household and person records in study area will be updated
# Existing records from hh_persons.h5 from other areas will be unchanged
# In cases where we want to update a full region we can turn this off and export all records as a new h5
if config['update_existing_h5']:    
    export_hh_df = old_h5_hh[~old_h5_hh['hhtaz'].isin(df_hh['hhtaz'])]
    export_hh_df = export_hh_df.append(df_hh[export_hh_df.columns])

    # Select persons from households within the final export list
    export_person_df = old_h5_person[old_h5_person['hhno'].isin(export_hh_df['hhno'])]
    export_person_df = export_person_df.append(new_person_df[old_h5_person.columns])
else:
    export_hh_df = df_hh.copy()
    export_person_df = new_person_df.copy()

# Write to h5 file
# Delete file if exists
if os.path.exists(popsim_run_dir_path/'output'/'hh_and_persons.h5'):
    os.remove(popsim_run_dir_path/'output'/'hh_and_persons.h5')

out_h5 = h5py.File(popsim_run_dir_path/'output'/'hh_and_persons.h5','w')
for key in ['Person','Household']:
    out_h5.create_group(key)
for col in myh5['Person'].keys():
    out_h5['Person'][col] = export_person_df[col].astype('int').values
for col in myh5['Household'].keys():
    out_h5['Household'][col] = export_hh_df[col].astype('int').values

out_h5.close()
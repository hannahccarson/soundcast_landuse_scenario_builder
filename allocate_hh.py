import geopandas as gpd
import pandas as pd
import numpy as np
from shapely import wkt
from shapely.geometry import Point
import sys
import subprocess

returncode = subprocess.call([sys.executable, 'PopulationSim/run_populationsim.py', '-w', 'PopulationSim'])
if returncode != 0:
    sys.exit(1)


model_dir = r'L:\vision2050\soundcast\dseis\integrated\final_runs\tod\tod_run_8.run_2018_10_29_15_01\2050'
data_gdb_path = r'R:\e2projects_two\Stefan\soundcast_landuse_scenario_builder\data\New File Geodatabase.gdb'
land_use_path = r'R:\e2projects_two\SoundCast\Inputs\dev\landuse\2050\test_2050'
output_dir = r'R:\e2projects_two\Stefan\soundcast_landuse_scenario_builder'

parcels = pd.read_csv(r'R:\e2projects_two\SoundCast\Inputs\dev\landuse\2050\test_2050\parcels_urbansim.txt', sep = ' ')
synth_hhs = pd.read_csv(r'R:\e2projects_two\Stefan\soundcast_landuse_scenario_builder\PopulationSim\output\synthetic_households.csv')

taz_id = 'taz'
block_group_id = 'geoid10'
puma_id = 'pumace10'
parcel_id = 'PARCELID'

df_list = []
for taz in synth_hhs['taz_id'].unique():
    taz_df = synth_hhs[synth_hhs['taz_id']==taz][['taz_id', 'hh_id', 'household_id']]
    taz_parcels = parcels.loc[parcels['taz_p']==taz]
    if taz_parcels['hh_p'].sum()==0:
        # if no exisiting HHs in TAZ
        # make every parcel have one
        taz_parcels['hh_p'] = 1
    taz_parcels = taz_parcels[taz_parcels['hh_p']>0][['taz_p', 'hh_p', 'parcelid']]
    taz_parcels = taz_parcels.loc[taz_parcels.index.repeat(taz_parcels['hh_p'])]
    taz_parcels = taz_parcels.sample(len(taz_df), replace = True)
    # merge HHs and their new parcels
    taz_parcels.reset_index(inplace=True)
    taz_df.reset_index(inplace = True)
    taz_df = taz_df.merge(taz_parcels, how = 'left', left_index = True, right_index = True)
    df_list.append(taz_df)

hh_parcels_df = pd.concat(df_list)
new_parcel_hhs_total = hh_parcels_df['parcelid'].value_counts()


df.loc[df.Code=='Dummy', 'Code'] = df.merge(df2, on='Market', how='left')['Code(New)']

df1.loc[to_update, 'score1'] = df1.loc[to_update,'team1'].map(to_map)


        # make each taz parcel have one hh to start





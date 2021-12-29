import geopandas as gpd
import pandas as pd
import numpy as np
import os, pyodbc, sqlalchemy, time
import networkx as nx
import time
from shapely import wkt
from shapely.geometry import Point
import h5py

def h5_to_data_frame(h5file, integer_cols, table_name):
    table = h5file[table_name]
    col_dict = {}
    #cols = ['hhno', 'hhtaz']
    for col in table.keys():
        if col == 'sov_ff_time':
            pass
        elif col in integer_cols:
            my_array = np.asarray(table[col]).astype('int')
        else:
            my_array = np.asarray(table[col])
        col_dict[col] = my_array.astype(float)
    return(pd.DataFrame(col_dict))

def update_df(target_df, target_index, update_df, update_index, col_name):
    target_df[col_name] = 0
    target_df.set_index(target_index, inplace = True)
    update_df.set_index(update_index, inplace = True)
    target_df.update(update_df)
    target_df.reset_index(inplace = True)
    update_df.reset_index(inplace = True)
    return target_df

def recode(df, col, new_col, bins, labels, group_by_col):
    category = pd.cut(df[col],bins=bins,labels=labels)
    if new_col in df.columns:
        df = df.drop(columns = [new_col])
    df.insert(len(bins), new_col, category)
    return pd.crosstab(df[group_by_col], df[new_col]).rename_axis(None, axis=1)
    #df = pd.DataFrame(df.groupby(group_by_col)[new_col].sum())

model_dir = r'L:\vision2050\soundcast\dseis\integrated\final_runs\tod\tod_run_8.run_2018_10_29_15_01\2050'
data_gdb_path = r'R:\e2projects_two\Stefan\soundcast_landuse_scenario_builder\data\New File Geodatabase.gdb'
land_use_path = r'R:\e2projects_two\SoundCast\Inputs\dev\landuse\2050\test_2050'
output_dir = r'R:\e2projects_two\Stefan\soundcast_landuse_scenario_builder'
taz_id = 'taz'
block_group_id = 'geoid10'
puma_id = 'pumace10'
parcel_id = 'PARCELID'
# Load GIS files:
block_group_gdf = gpd.read_file(data_gdb_path, layer = 'block_groups_2010')

taz_study_area = gpd.read_file(data_gdb_path, layer = 'study_area_taz')

puma_gdf = gpd.read_file(data_gdb_path, layer = 'pumas_2010')

# parcels
parcels_gdf = pd.read_csv(os.path.join(model_dir, 'inputs\scenario\landuse\parcels_urbansim.txt'), sep = ' ')
geometry = [Point(xy) for xy in zip(parcels_gdf['XCOORD_P'], parcels_gdf['YCOORD_P'])]
parcels_gdf = parcels_gdf.drop(['YCOORD_P', 'XCOORD_P'], axis=1)
parcels_gdf = gpd.GeoDataFrame(parcels_gdf, crs="EPSG:2285", geometry=geometry)

# hhs and persons:
hdf_file = h5py.File(os.path.join(land_use_path, 'hh_and_persons.h5'), "r")
persons = h5_to_data_frame(hdf_file, ['id'], 'Person')
hh = h5_to_data_frame(hdf_file, ['id'], 'Household')

#get parcels that are withing the TAZ layer
parcels_cols = list(parcels_gdf.columns)
parcels_cols.extend([taz_id, block_group_id, puma_id])

parcels_gdf = gpd.sjoin(parcels_gdf, taz_study_area, how='inner')
parcels_gdf = parcels_gdf[[col for col in parcels_cols if col in parcels_gdf.columns]]

#now get block_groups that are covered by parcels
parcels_gdf = gpd.sjoin(parcels_gdf, block_group_gdf, how='inner')
parcels_gdf = parcels_gdf[[col for col in parcels_cols if col in parcels_gdf.columns]]

# its possible that a TAZ could fall in more than 1 PUMA
# so use the one that the TAZ centroid falls in. 
taz_points = taz_study_area.copy()
taz_points.geometry = taz_points.geometry.centroid
taz_puma_gdf = gpd.sjoin(taz_points, puma_gdf, how='inner')
taz_puma_gdf = taz_puma_gdf[[taz_id, puma_id]]
taz_puma_gdf['region'] = 1

##### write out popsim geog file
taz_puma_gdf.rename(columns={taz_id:'taz_id', puma_id:'PUMA'}, inplace = True)
for col in taz_puma_gdf.columns:
    taz_puma_gdf[col] = taz_puma_gdf[col].astype('int64')

taz_puma_gdf.to_csv(os.path.join(output_dir, 'Populationsim/data/geo_cross_walk.csv'), index = False)



#####Build controls from future land use

study_area_hhs = hh[hh['hhparcel'].isin(parcels_gdf[parcel_id])]
study_area_hhs = update_df(study_area_hhs, 'hhparcel', parcels_gdf, parcel_id, taz_id)

study_area_persons = persons[persons['hhno'].isin(study_area_hhs['hhno'])]
study_area_persons = update_df(study_area_persons, 'hhno', study_area_hhs, 'hhno', taz_id)

#get hh workers from person table
workers = study_area_persons[study_area_persons['pwtyp']>0]
hh_workers = workers.groupby('hhno').size().reset_index()
hh_workers = hh_workers.rename(columns={0:'hhwkrs'})
study_area_hhs = update_df(study_area_hhs, 'hhno', hh_workers, 'hhno', 'hhwkrs')


col_list = []
####### hh categories
# total households:
col_list.append(pd.DataFrame(study_area_hhs.groupby(taz_id).size(), columns = ['hh_taz_weight']))
# hh size:
col_list.append(recode(study_area_hhs, 'hhsize', 'num_hh', [0, 1, 2, 3, 4, 5, 6, 200], ['hh_size_1','hh_size_2', 'hh_size_3', 'hh_size_4', 'hh_size_5', 'hh_size_6', 'hh_size_7_plus'], taz_id))
# workers:
col_list.append(recode(study_area_hhs, 'hhwkrs', 'num_workers', [-1, 0, 1, 2, 999], ['workers_0','workers_1', 'workers_2', 'workers_3_plus'], taz_id))
# income 
col_list.append(recode(study_area_hhs, 'hhincome', 'income_cat', [-1, 15000, 30000, 60000, 100000, 999999999], ['income_lt15','income_gt15-lt30', 'income_gt30-lt60', 'income_gt60-lt100', 'income_gt100'], taz_id))


####### persons categories
# total persons
col_list.append(pd.DataFrame(study_area_persons.groupby(taz_id).size(), columns = ['pers_taz_weight']))
# school:
col_list.append(recode(study_area_persons, 'pstyp', 'school', [-1, 0, 100], ['school_no','school_yes'], taz_id))
# gender:
col_list.append(recode(study_area_persons, 'pgend', 'gender', [0, 1, 100], ['male','female'], taz_id))
# age:
col_list.append(recode(study_area_persons, 'pagey', 'age', [-1, 19, 35, 60, 999], ['age_19_and_under', 'age_20_to_35', 'age_35_to_60', 'age_above_60'], taz_id))
# worker_status
col_list.append(recode(study_area_persons, 'pwtyp', 'worker', [0, 999], ['is_worker'], taz_id))

df = pd.concat(col_list, axis = 1)
df.reset_index(inplace = True)
df.rename(columns={taz_id:'taz_id'}, inplace = True)
df['taz_id'] = df['taz_id'].astype('int64')
df.fillna(0, inplace = True)
#df['block_group_id'] = df[geoid_name]

df.to_csv(os.path.join(output_dir, 'Populationsim/data/future_controls.csv'), index = False)

# seed hh and persons
seed_hh = pd.read_csv(r'R:\e2projects_two\SyntheticPopulation_2018\keep\2018\populationsim_files\data\seed_households.csv')
seed_hh = seed_hh[seed_hh['PUMA'].isin(taz_puma_gdf['PUMA'])]
seed_hh.to_csv(os.path.join(output_dir, 'Populationsim/data/seed_households.csv'), index = False)

seed_persons = pd.read_csv(r'R:\e2projects_two\SyntheticPopulation_2018\keep\2018\populationsim_files\data\seed_persons.csv')
seed_persons = seed_persons[seed_persons['hhnum'].isin(seed_hh['hhnum'])]
seed_persons.to_csv(os.path.join(output_dir, 'Populationsim/data/seed_persons.csv'), index = False)
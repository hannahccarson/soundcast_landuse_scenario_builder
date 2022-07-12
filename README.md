# Soundcast Landuse Scenario Builder

This tool is used to modify Soundcast landuse inputs. Users can specify households totals for target zones and Soundcast-formatted inputs will be produced. Population distributions from Vision 2050 will be applied to all changes, which maintains underlying policy/forecast assumptions while allowing users to change detailed locations of households at a zonal level. This tool parcelizes these changes and updates Soundcast's synthetic population files to allow scenario testing. 

An example directory is included to show how the tool should be run. 

## Install and Setup
Clone this repository or download code directly to working directory.

This repository includes an Anaconda environment with all required libraries to run the tool, including the PopulationSim library used to produce the synthetic population files. To install the environment, open an Anaconda prompt in the clone directory root and run:

    conda env create -f environment.yml
    
After installing this environment, activate it as follows. This environment must be activated every time a new prompt is opened.
    
    conda activate soundcast_landuse

## Inputs
The tool requires inputs from multiple sources. The example folder contains 2 directories of input that are required to run the tool.
- data
    - geo_cross_walk.csv
    - seed_household.csv: PUMS seed household records; these seed households are replicated by PopulationSim to match zonal demographic distributions
    - seed_persons.csv: PUMS seed person records
    - Zone system geodatabase: ArcGIS geodatabase that contains layers of zones included in the landuse changes
- input
    - allocation.csv

### Configuring Inputs
These data are required, but their location can be set and changed in config.yaml, located in the project root. Additional paths must also be defined, which point to inputs that are generally accessed from other (non-local) locations. These are often large files part of an existing Soundcast run. The following are paths and definitions that should be checked before running. The default is set to run the included example run by default.

- data_dir: location of data referenced above
- input_dir: specification of total households and jobs in a study area
- data_gdb_path: ArcGIS geodatabase that contains layers of zones included in the landuse changes
- seed_hh_file: PUMS seed household records file name (assumed to be stored under data_dir folder)
- seed_person_file: PUMS seed person records file name (assumed to be stored under data_dir folder)
- model_dir: location of a Soundcast run that contains inputs that will be modified by this tool
- land_use_path: location of a Soundcast run used to define demographic distributions; these are held constant as the totals are changed by the user


The primary purpose of this tool is to apply TAZ-level household and emplyoment adjustments to generate Soundcast inputs. These changes are made in **inputs\allocation.csv**. For any zone in the study area, users can set the new total number of households in a zone by updating the "households" field. Total employment may also be updated based on the "employment" field. Currently, only TAZs within the study may be updated for either employment or households. Whatever values are provided for in the allocation.csv file will be applied as scaling factors to the data. If you prefer not to apply either of these measures, they can turned off in config.yaml as follows:

    - update_jobs: False
    - update_hh: False
    
In the example run, total households for a small set of zones are grown at a fixed percent and jobs in all these areas set to a fixed number of 1,000 jobs per zone. The may be edited in the allocation.csv file. 

## Scripts
Two scripts are required to produce the Soundcast input files. 

### Generate Controls
The first to be run is **generate_controls.py**. After populating input directories in config.yaml, this script be run with

     python generate_controls.py

This script generates the necessary inputs to generate the synthetic household and population files for a defined study area. Based on zones included in the GeoDatabase, a set of PopulationSim control files and other inputs are generated. Seed records are selected from the study area and used to produce the refined synthetic populations. The outputs from this process will be available in the *PopulationSim\data* directory:
     - future_controls.csv: primary control totals for all controlled variables within the study area. 
         - Users can edit the **hh_taz_weight** field to change the total number of households per zone. 
     - geo_cross_walk.csv: geographic relationship between input zones and PUMAs (relating the seed files to the study area)
     - seed_households.csv: subset of seed households located within the study area; only these will be used to run PopulationSim in the next step
     - seed_persons.csv: subset of seed persons 
     
### Allocate Households
The second script to be run is **allocate_hh.py**. 

    python allocate_hh.py
    
This script uses the outputs of *generate_controls.py* to run PopulationSim and update Soundcast inputs with edited zone-level controls. The inputs required for this script are the outputs from the previous script. This script directly calls PopulationSim, which produces a set of synthetic household and person files for the study area. These synthetic data replace existing houeshold and person data for these zones and are written to file for use in a new Soundcast scenario run. Final outputs are available in the **results** folder:
- parcels_urbansim.txt: Soundcast parcel-level landuse file, updated for total number of households per parcel
- hh_and_persons.h5: Soundcast synthetic household and person data, updated to reflect land use changes. 
    

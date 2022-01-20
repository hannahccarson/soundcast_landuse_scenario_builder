# Soundcast Landuse Scenario Builder

This tool is used to modify Soundcast landuse inputs. Users can specify households totals for target zones and Soundcast-formatted inputs will be produced. Population distributions from Vision 2050 will be applied to all changes, which maintains underlying policy/forecast assumptions while allowing users to change detailed locations of households at a zonal level. This tool parcelizes these changes and updates Soundcast's synthetic population files to allow scenario testing. 

## Install and Setup
This repository includes an Anaconda environment with all required libraries to run the tool, including the PopulationSim library used to produce the synthetic population files. To install the environment, open an Anaconda prompt in the clone directory root and run:

    conda env create -f environment.yml
    
After installing this environment, activate it as follows. This environment must be activated every time a new prompt is opened.
    
    conda activate scenario_landuse

## Inputs
The tool requires inputs from multiple sources. Paths to inputs are set in the config.yaml file in the project root directory. 
- seed_hh_file: PUMS seed household records; these seed households are replicated by PopulationSim to match zonal demographic distributions
- seed_person_file: PUMS seed person records
- model_dir: location of a Soundcast run that is to be modified
- data_gdb_path: ArcGIS geodatabase that contains layers of zones included in the landuse changes
- land_use_path: location of a Soundcast run used to define demographic distributions; these are held constant as the totals are changed by the user

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
    

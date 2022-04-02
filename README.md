# Soundcast Landuse Scenario Builder

This tool is used to modify Soundcast landuse inputs. Users can specify households totals for target zones and Soundcast-formatted inputs will be produced. Population distributions from Vision 2050 will be applied to all changes, which maintains underlying policy/forecast assumptions while allowing users to change detailed locations of households at a zonal level. This tool parcelizes these changes and updates Soundcast's synthetic population files to allow scenario testing. 


## Install and Setup
Clone this repository or download code directly to working directory.

This repository includes an Anaconda environment with all required libraries to run the tool, including the PopulationSim library used to produce the synthetic population files. To install the environment, open an Anaconda prompt in the clone directory root and run:

    conda env create -f environment.yml
    
After installing this environment, activate it as follows. This environment must be activated every time a new prompt is opened.
    
    conda activate scenario_landuse

## Inputs

The tool requires standard inputs. [Users can download example input data here](https://file.ac/zMj1JWnmnGg/). Each of the following folder locations must be specified in config.yaml.
- land_use
     - hh_and_persons.h5: existing Soundcast synthetic household and population file
     - parcels_urbansim.txt: Soundcast land use file to be used for distribution controls 
- pums_data
    - seed_household.csv: PUMS seed household records; these seed households are replicated by PopulationSim to match zonal demographic distributions
    - seed_persons.csv: PUMS seed person records
- gis_data.gdb: geodatabase containing zone shapefile of zones that are to be changed. 

Note that in the [provided example data](https://file.ac/zMj1JWnmnGg/) the land_use folder contains a "2050" sub-directory. This designates this data as 2050. Users can add additional years or scenarios here and should update the config setting "input_land_use_path" to full path of the desired directory.

### Configuring Inputs
Once data has been provided, the location of this data must be specified in config.yaml. The following input locations must be updated by the user before running:

- input_land_use_path
- input_pums_data_path
- input_gis_data_path

Users must also update the **'output_dir'** field to specify where the outputs and intermediate data should be stored.

Additional variables in the config should not need to be changed unless the users wants to customize field names. 

With these settings configured, the first step of the tool can be run. After the first step, users can make changes to the land use allocation before running the second step, which will produce the final outputs. These steps are described in detail below. 

## Running the Tool
Two scripts are required to produce the Soundcast input files. 

### Generate Controls
The first to be run is **generate_controls.py**. After populating input directories in config.yaml, this script can be run with

     python generate_controls.py

This script generates the necessary inputs to generate the synthetic household and population files for a defined study area. Based on zones included in the GeoDatabase, a set of PopulationSim control files and other inputs are generated. Seed records are selected from the study area and used to produce the refined synthetic populations. The outputs from this process will be available in the location specified in 'output_dir' in config.yaml, and will include the following:
    - configs: files used internally by populationsim
    - data: populationsim inputs
        - **user_allocation.csv**: primary file that users will edit, described below
        - future_controls.csv: detailed file that describes zone-level control totals for populationsim. 
    - output
        - all outputs of populationsim and this tool, which will be available after running the next script
        
The **user_allocation.csv** file is the main control of total households and jobs by zone. Users should change totals only for zones they wish to update. 
     
### Allocate Households
The second script to be run is **allocate_hh.py**. 

    python allocate_hh.py
    
This script uses the outputs of *generate_controls.py* to run PopulationSim and update Soundcast inputs with edited zone-level controls. The inputs required for this script are the outputs from the previous script. This script directly calls PopulationSim, which produces a set of synthetic household and person files for the study area. These synthetic data replace existing houeshold and person data for these zones and are written to file for use in a new Soundcast scenario run. Final outputs are available in the **output** folder:
- parcels_urbansim.txt: Soundcast parcel-level landuse file, updated for total number of households per parcel
- hh_and_persons.h5: Soundcast synthetic household and person data, updated to reflect land use changes. 
    

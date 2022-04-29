# Soundcast Landuse Scenario Builder

This tool is used to modify Soundcast landuse inputs. Users can specify households totals for target zones and Soundcast-formatted inputs will be produced. Population distributions from Vision 2050 will be applied to all changes, which maintains underlying policy/forecast assumptions while allowing users to change detailed locations of households at a zonal level. This tool parcelizes these changes and updates Soundcast's synthetic population files to allow scenario testing. 


## Install and Setup
Clone this repository or download code directly to working directory.

This repository includes an Anaconda environment with all required libraries to run the tool, including the PopulationSim library used to produce the synthetic population files. To install the environment, open an Anaconda prompt in the clone directory root and run:

    conda env create -f environment.yml
    
After installing this environment, activate it as follows. This environment must be activated every time a new prompt is opened.
    
    conda activate scenario_landuse

## Inputs

The tool requires standard inputs. [Users can download example input data here](https://file.ac/zMj1JWnmnGg/). Unzip these folders to a convenient location on your local machine. For example purposes, we will assume the data has been extracted to `C:\users\test\landuse_scenario_test`. Each of the following paths must then be specified in **config.yaml** in this repository.

### Configuring Inputs
Once data has been provided, the location of this data must be specified in config.yaml. The following input locations must be updated by the user before running.

- input_land_use_path
  - Soundcast parcel and synthetic population files. 
     - The parcel file (parcels_urbansim.txt) will be used to allocate households from TAZ-level controls to parcels. The parcel file used here will determine the spatial detail of any changes to land use at a zone level and will ensure results are based on some desired distribution. For instance, using a 2050 parcel file with PSRC's Vision 2050 policies will ensure that households and jobs are distributed across zones with this same policy reference, even with changes in zone-level totals. 
     - If the tool is being run for only a portion of the region (a specific study area), the synthetic household and persons data (hh_and_persons.h5) will be updated with any changes, leaving all other households and persons the same. The user must specify this with the variable **update_existing_h5**. When True, the data from this input hh_and_persons.h5 will be copied and updated where appropriate. When False, an entirely new synthetic population file will be generated, which should only be done when performing a regional-scale analysis. 
- input_pums_data_path
  - should include PUMS person and household records; these are the files that will be closed by populationsim to produce a synthetic population
      - seed_household.csv
      - seed_persons.csv
- input_gis_data_path
  - a geodatabase

For the example data, these should be set as follows (updating to your local data directory where appropriate)
- input_land_use_path: <C:\users\test\landuse_scenario_test\>land_use\2050
- input_pums_data_path: <C:\users\test\landuse_scenario_test\>pums_data
- input_gis_data_path: <C:\users\test\landuse_scenario_test\>gis_data.gdb

File names should not be changed for the example data but users are welcome to change these as needed. 

Make sure to update the **output_dir** field to a convenient location on your machine. This will be the location where populationsim inputs and outputs of the tool are created. Note that this directory will be overwritten when the scripts are run.

As mentioned above, set **updated_existing_h5** to True for the example, which will use the supplied synthetic population file (hh_and_persons.h5), located in the input_land_use_path, as the basis for editing population for a study area. In general, this variable should be True for any study area analysis and False only when running for the full region.

Users can turn off some portions of the to only allocate jobs, households, persons (or any combination of those) with the following settings. These should be kept as True for the example:
- update_jobs
- update_hh
- update_persons

Finally, column names can be changed if required for other data sets, but these should generally remain unchanged. 

Note that in the [provided example data](https://file.ac/zMj1JWnmnGg/) the land_use folder contains a "2050" sub-directory. This designates this data as 2050. Users can add additional years or scenarios here and should update the config setting "input_land_use_path" to full path of the desired directory. 

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
    

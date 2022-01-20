# Soundcast Landuse Scenario Builder

This tool is used to modify Soundcast landuse inputs. Users can specify households totals for target zones and Soundcast-formatted inputs will be produced. Population distributions from Vision 2050 will be applied to all changes, which maintains underlying policy/forecast assumptions while allowing users to change detailed locations of households at a zonal level. This tool parcelizes these changes and updates Soundcast's synthetic population files to allow scenario testing. 

## Install
This repository includes an Anaconda environment with all required libraries to run the tool, including the PopulationSim library used to produce the synthetic population files. To install the environment, open an Anaconda prompt in the clone directory root and run:

    conda env create -f environment.yml
    
After installing this environment, activate it as follows. This environment must be activated every time a new prompt is opened.
    
    conda activate scenario_landuse

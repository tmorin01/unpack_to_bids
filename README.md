# General Info
Author: Tom Morin (tommorin), Boston University
Date: February, 2020
Purpose: Python script for unpacking MRI DICOM data into BIDS format

# Required Modules:
       On the SCC, load the following modules before running these scripts:
       module load dcm2niix
       module load python3

# Usage: 
       python unpack_to_bids.py [OPTIONS]
       python unpack_to_bids.py -h  ## Displays help information and possible flags

# Notes: 
       This script is still under development. Contact tommorin@bu.edu with any
       errors or bugs.

# Files in this Repo:
    README.md: You're reading it
    unpack_to_bids.py: Main script that unpacks DICOM images to BIDS format
    unpack_to_bids_RPMS_2001.sh: example of how to call unpack_to_bids.py for
                                 one subject



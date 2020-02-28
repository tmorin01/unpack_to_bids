#!/usr/bin/python

""" 
unpack_to_bids.py

  Author: Tom Morin
    Date: March, 2019
 Purpose: Unpack DICOM images into BIDS format for a specific subject and session
"""

################################################################################
#
# IMPORT USEFUL PYTHON MODULES
#
################################################################################
import sys
import argparse
import json
import os
import shutil
import datetime
import re
import numpy
import subprocess

################################################################################
#
# DEFINE CONSTANT VARIABLES
#
################################################################################
BIDS_VERSION = "1.0.2"

################################################################################
#
# IMPLEMENT USEFUL FUNCTIONS
#
################################################################################
# Implement Unix's "touch" command in Pyton to create new blank files
def touch(path):
    with open(path, 'a'):
        os.utime(path, None)

# Prepend to a text file
def prepend(filename, line):
    with open(filename, "r+") as f:
        content = f.read()
        f.seek(0,0)
        f.write(line.rstrip('\r\n') + '\n' + content)

def check_args(args):
    if args.sub is None:
        sys.exit("ERROR: No --sub argument specified")
    if args.sess is None:
        sys.exit("ERROR: No --sess argument specified")
    if args.input_dir is None:
        sys.exit("No --input_dir argument specified")
    if args.output_dir is None:
        sys.exit("No --output_dir argument specified")

# Copy scans from XNAT-Unpacked, to BIDS-compliant directory
def copy_to_bids(runs, img_type, this_sess, fmap_apply = []):
    print("Copying the following files into " + img_type)
    for i in range(0,len(runs)):
        run_number = runs[i][0]
        fname = runs[i][1]
    
        # Create img_type folder if it doesn't exist
        if not os.path.exists(os.path.join(this_sess, img_type)):
            print("Creating directory for " + img_type + " data.")
            os.mkdir(os.path.join(this_sess, img_type))
    
        # Move files ending with run_number.nii and run_number.json into the BIDS dir
        if len(os.listdir(os.path.join(input_dir, "UNPACKED"))) <= 1:
            print("No files found in input directory: " + os.path.join(input_dir, "UNPACKED"))
        for f in os.listdir(os.path.join(input_dir, "UNPACKED")):
            if f.endswith("_" + run_number + ".nii"):
                print("---- " + fname + ".nii")
                shutil.copy(os.path.join(input_dir, "UNPACKED", f), 
                            os.path.join(this_sess, img_type, fname + ".nii"))
            elif f.endswith("_" + run_number + ".json"):
                print("---- " + fname + ".json")
                shutil.copy(os.path.join(input_dir, "UNPACKED", f), 
                            os.path.join(this_sess, img_type, fname + ".json"))
                if img_type == 'func':
                    fpath = os.path.join(this_sess, img_type, fname + ".json")
                    update_task(fpath, fname)
                if img_type == 'fmap':
                    print("-------- Updating IntendedFor Field in .json file")
                    fpath = os.path.join(this_sess, img_type, fname + ".json")
                    update_intended_for(fpath, fname, fmap_apply)
            elif f.endswith("_" + run_number + ".bval"):
                print("---- " + fname + ".bval")
                shutil.copy(os.path.join(input_dir, "UNPACKED", f), 
                            os.path.join(this_sess, img_type, fname + ".bval"))
            elif f.endswith("_" + run_number + ".bvec"):
                print("---- " + fname + ".bvec")
                shutil.copy(os.path.join(input_dir, "UNPACKED", f), 
                            os.path.join(this_sess, img_type, fname + ".bvec"))

def update_intended_for(fpath, fname, fmap_apply):
    intended_for = []
    for i in range(0,len(fmap_apply)):
	if fname == fmap_apply[i][0]:
            intended_for = fmap_apply[i][1:]
            with open(fpath, 'r+') as outfile:
                data = json.load(outfile)
                data['IntendedFor'] = intended_for
                outfile.seek(0)
                json.dump(data, outfile, indent=4)
                outfile.close()

def update_task(fpath, fname):
    tags = fname.split("_")
    tags = ["modality-" + tag if "-" not in tag else tag for tag in tags]
    tags = dict(s.split("-") for s in tags)
    print("-------- Updating TaskName Field in .json file")
    with open(fpath, 'r+') as outfile:
        data = json.load(outfile)
        data['TaskName'] = tags['task']
        outfile.seek(0)
        json.dump(data, outfile, indent=4)
        outfile.close()

def fname_error(fname, message):
    sys.exit("ERROR: Bad filename: " + fname + "\n" + message)

# Check if a tag exists. Throw an error if it exists but isn't alphanumeric
def check_tag_alnum(fname, tags, tag, tag_type):
    if tag in tags:
        if not tags[tag].isalnum():
            fname_error(fname, tag_type + " tag " + tags[tag] + " contains non-alphanumeric characters")
        return True
    else:
        return False

# Check if a tag exists. Throw an error if it exists but isn't entirely numeric
def check_tag_digits(fname, tags, tag, tag_type):
    if tag in tags:
        if not tags[tag].isdigit():
            fname_error(fname, tag_type + " tag " + tags[tag] + " must only contain digits")
        return True
    else:
        return False

# Check if the file tail (modality tag) is BIDS-valid
def check_ftail(fname, tags, img_type):
    ex_modalities = {'anat':'T1w', 'func':'bold', 'dwi':'dwi', 'fmap':'phasediff or magnitude'}
    anat_modes = ['T1w', 'T2w', 'T1rho', 'T1map', 'T2map', 'T2star', 'FLAIR', 'FLASH', 'PD', 
                  'PDT2', 'inplaneT1', 'inplaneT2', 'angio', 'defacemask', 'SWImagandphase']
    func_modes = ['bold', 'sbref']
    dwi_modes = ['dwi']
    fmap_modes = ['phasediff', 'magnitude', 'phase1', 'phase2', 'magnitude1', 'magnitude2', 'fieldmap', 'epi']

    if 'modality' not in tags:
        fname_error(fname, "Could not find modality tag at the end of the filename. For example, a " + 
                            img_type + " image would include '" + ex_modalities[img_type] + "' at the end of the filename.")
    elif not tags['modality'].isalnum():
        fname_error(fname, "Modality tag '" + tags['modality'] + "' contains non-alphanumeric characters")
    
    if img_type=="anat":
        if tags['modality'] not in anat_modes:
            fname_error(fname, tags['modality'] + " not supported for anat images. Choose from: " + str(anat_modes))
    elif img_type=="func":
        if tags['modality'] not in func_modes:
            fname_error(fname, tags['modality'] + " not supported for func images. Choose from: " + str(func_modes))
    elif img_type=="dwi":
        if tags['modality'] not in dwi_modes:
            fname_error(fname, tags['modality'] + " not supported for dwi images. Choose from: " + str(dwi_modes))
    elif img_type=="fmap":
        if tags['modality'] not in fmap_modes:
            print("WARNING: " + "Potentially bad filename: " + fname + "\n" +
                  tags['modality'] + " might not be a good tag for a fieldmap. Suggested tags: " +
                  str(fmap_modes))
            
# Check if a user-specified filename is BIDS compatible
def check_filename(fname, img_type):
    tags = fname.split("_")
    tags = ["modality-" + tag if "-" not in tag else tag for tag in tags]
    tags = dict(s.split("-") for s in tags)
    
    # Check sub tag (MANDATORY)
    if not check_tag_alnum(fname, tags, 'sub', 'Subject'):  
        fname_error(fname, "Filename should start with 'sub-PARTICIPANT' tag")  

    # Check ses tag (OPTIONAL)
    check_tag_alnum(fname, tags, 'ses', 'Session')

    # Check file tail (modality tag and filetype)
    check_ftail(fname, tags, img_type)

    # Check ANAT images:
    if img_type == "anat":
        check_tag_alnum(fname, tags, 'acq', 'Acquisition')
        check_tag_alnum(fname, tags, 'ce', 'Contrast Enhancement')
        check_tag_alnum(fname, tags, 'rec', 'Reconstruction')
        check_tag_alnum(fname, tags, 'mod', 'Modalities Ref')
        check_tag_digits(fname, tags, 'run', 'Run')
    # Check FUNC images:
    elif img_type == "func":
        if not check_tag_alnum(fname, tags, 'task', 'Task'):
            fname_error(fname, "Functional filename must contain 'task-DESCRIPTION' tag")
        check_tag_alnum(fname, tags, 'rec', 'Reconstruction')
        check_tag_digits(fname, tags, 'run', 'Run')
        check_tag_digits(fname, tags, 'echo', 'Echo')
    # Check DWI images:
    elif img_type == "dwi":
        check_tag_alnum(fname, tags, 'acq', 'Acquisition')
        check_tag_digits(fname, tags, 'run', 'Run')
    # Check FIELDMAP images:
    elif img_type == "fmap":
        check_tag_alnum(fname, tags, 'acq', 'Acquisition')
        check_tag_digits(fname, tags, 'run', 'Run')
        check_tag_alnum(fname, tags, 'dir', 'DIR')

################################################################################
#
# CHECK FOR NECESSARY SCC MODULES
#
################################################################################
# NEEDSWORK: Check to see if mricrogl module was loaded

################################################################################
#
# MAIN SCRIPT
#
################################################################################
# ==============================================================================
# Parse input arguments (also specify help info)
# ==============================================================================
print("Running unpack_to_bids.py")
print("Parsing arguments")
parser = argparse.ArgumentParser()
parser.add_argument('-s', '--sub', 
                    help="subject ID (e.g. RPMS2001)")
parser.add_argument('-e', '--sess', 
                    help="session number")
parser.add_argument('-i', '--input_dir', 
                    help="project directory where DICOM images are stored (e.g. output of xnat2proj command)")
parser.add_argument('-o', '--output_dir', 
                    help="output directory where NIFTI & JSON files will be stored in BIDS format")
parser.add_argument('-a', '--anat', 
                    action='append', 
                    nargs=2, 
                    metavar=('RUN_NUM','FILENAME'),
                    default=[],
                    help="for an anatomical scan, specify the run number and the BIDS-format file name")
parser.add_argument('-f', '--func', 
                    action='append', 
                    nargs=2, 
                    metavar=('RUN_NUM','FILENAME'),
                    default=[],
                    help="for a functional scan, specify the run number and the BIDS-format file name")
parser.add_argument('-d', '--dwi', 
                    action='append', 
                    nargs=2, 
                    metavar=('RUN_NUM','FILENAME'),
                    default=[],
                    help="for a diffusion weighted scan, specify the run number and the BIDS-format file name")
parser.add_argument('-m', '--fmap', 
                    action='append', 
                    nargs=2, 
                    metavar=('RUN_NUM','FILENAME'),
                    default=[],
                    help="for a fieldmap, specify the run number and the BIDS-format file name")
parser.add_argument('-n', '--intended_for',
                    action='append',
                    default=[],
                    nargs='+',
                    type=int,
                    help="a list of integers. First indicates a fieldmap run, the rest specify which functional runs the fmap should be used with, (e.g. for distortion correction)")
parser.add_argument('-p', '--proj_name',
                    default="A neuroimaging project",
                    help="Name of project for dataset_description.json file")
parser.add_argument('-c', '--change', 
                    action='append', 
                    nargs=2, 
                    metavar=('VERSION', 'DESCRIPTION'),
                    default=[['9.9.9','No message provided by user regarding these changes']], 
                    help="version number and description of changes for the CHANGES log file")
args = parser.parse_args()

# Check that mandatory flags were given
check_args(args)

# Assign input arguments to more convenient variable names
sub = args.sub
bids_sub = re.sub('[^0-9a-zA-Z]+', '', sub) #Create a BIDS-compliant sub name, in case subject name contains non-alphanum chars
if bids_sub != sub:
    print("WARNING: " + sub + ", the subject name you provided, is not BIDS compliant. Using " + bids_sub + " instead.")
sess = args.sess
proj_name = args.proj_name
input_dir = args.input_dir
output_dir = args.output_dir
anat_runs = args.anat
dwi_runs = args.dwi
fmap_runs = args.fmap
func_runs = args.func
changes = args.change
fmap_apply = args.intended_for

# ==============================================================================
# Parse the -intended_for argument
# ==============================================================================
# Handle default case for Fieldmap "IntendedFor" field of json file
# (e.g. make all fieldmaps apply to all functional scans, by default)
if len(fmap_apply) > len(fmap_runs):
    sys.exit("ERROR: Too many --intended_for flags. Found " + str(len(fmap_runs)) + 
             " fieldmaps, but " + str(len(fmap_apply)) + " --intended_for flags.")
elif len(fmap_apply) < len(fmap_runs):
    print("WARNING: --intended_for flag not specified for all fieldmaps." + 
          " Unspecified fieldmaps will be IntendedFor ALL functional runs")
    for i in range(0,len(fmap_runs)):
        intended_for = []
        already_specified = False
        intended_for.append(int(fmap_runs[i][0]))
        for j in range(0,len(func_runs)):
            intended_for.append(int(func_runs[j][0]))
        # Check to see if IntendedFor was already specified
        for m in range(0,len(fmap_apply)):
            if intended_for[0] == fmap_apply[m][0]:
                already_specified = True
        if not already_specified:        
            fmap_apply.append(intended_for)

# Convert IntendedFor from run numbers to filenames
fmap_apply_names = []
for i in range(0,len(fmap_apply)):
    names = []
    # Append relevant fieldmap filename first
    for j in range(0,len(fmap_runs)):
        if fmap_apply[i][0] == int(fmap_runs[j][0]):
            names.append(fmap_runs[j][1])
    # Append all functional filenames next
    for j in range(0,len(fmap_apply[i])):
        for k in range(0,len(func_runs)):
            if fmap_apply[i][j] == int(func_runs[k][0]):
                names.append('ses-' + str(sess) + '/func/' + func_runs[k][1] + '.nii')
        for k in range(0,len(anat_runs)):
            if fmap_apply[i][j] == int(anat_runs[k][0]):
                names.append('ses-' + str(sess) + '/anat/' + anat_runs[k][1] + '.nii')
        for k in range(0,len(dwi_runs)):
            if fmap_apply[i][j] == int(dwi_runs[k][0]):
                names.append('ses-' + str(sess) + '/dwi/' + dwi_runs[k][1] + '.nii')
    fmap_apply_names.append(names)

# ==============================================================================
# Lightweight checks that filenames are generally BIDS-compliant
# ==============================================================================
# Check a few things
if not sub.isalnum():
    print('Creating BIDS-compliant subject name...\n----Original: ' + sub + '\n----Final: ' + bids_sub)

for run in anat_runs:
    check_filename(run[1], "anat")

for run in func_runs:
    check_filename(run[1], "func")

for run in dwi_runs:
    check_filename(run[1], "dwi")

for run in fmap_runs:
    check_filename(run[1], "fmap")

# ==============================================================================
# Convert DCM to NII & JSON using dcm2niix
# ==============================================================================
print("Converting DICOMS to NII")
if not os.path.exists(os.path.join(input_dir, "UNPACKED")):
    print("----Creating Directory for unpacked Images: " + os.path.join(input_dir, "/UNPACKED"))
    os.mkdir(os.path.join(input_dir, "UNPACKED"))
subprocess.call(["dcm2niix", "-f", "%i_%p_%t_%s", 
                             "-z", "n",
                             "-o", input_dir + "/UNPACKED", 
                             input_dir]) 

# ==============================================================================
# Create first level directories and metadata files
# ==============================================================================
# Create NIFTI (output) directory
if not os.path.exists(output_dir):
    print("Creating Output directory at: " + output_dir)
    os.mkdir(output_dir)
else:
    print("Output directory exists. Using: " + output_dir)

# Create or update dataset_description.json
fpath = os.path.join(output_dir, 'dataset_description.json')
if not os.path.exists(fpath):
    print("Creating dataset_description.json file")
    with open(fpath, 'w+') as outfile:
        data = {}
        data['Name'] = proj_name
        data['BIDSVersion'] = BIDS_VERSION
        outfile.seek(0)
        json.dump(data, outfile, indent=4)
        outfile.close()
else:
    print("Updating existing dataset_description.json file")
    with open(fpath, 'r+') as outfile:
        print("output file is %s" % outfile)
        data = json.load(outfile)
        data['BIDSVersion'] = BIDS_VERSION
        outfile.seek(0)
        json.dump(data, outfile, indent=4)
        outfile.close()

# Create or update README
print("Creating README")
with open(os.path.join(output_dir, 'README'), 'w+') as outfile:
    outfile.write("Project Name: " + proj_name + "\n")
    outfile.write("BIDS Version: " + BIDS_VERSION + "\n")
    now = datetime.datetime.now()
    outfile.write("This project was unpacked and put into BIDS format by unpack_to_bids.py on " + 
                  now.strftime("%Y-%m-%d %H:%M") + "\n")

# Create or update CHANGES file
fpath = os.path.join(os.path.join(output_dir, 'CHANGES'))
if not os.path.exists(fpath):
    print("Creating CHANGES file")
    with open(fpath, 'w+') as outfile:
        outfile.write("1.0.0 " + str(datetime.date.today()) + "\n")
        outfile.write("\t- Initial release.\n")
        outfile.close()
else:
    print("Updating changes file with the message specified by the --change option:\n" + changes[-1][1])
    prepend(fpath, 
            (changes[-1][0] + " " + str(datetime.date.today()) + '\n' +
             '\t- ' + changes[-1][1] + '\n'))

# Make "code directory"
fpath = os.path.join(output_dir, 'code')
if not os.path.exists(fpath):
    print("Creating code directory")
    os.mkdir(fpath)

# Make Subject Directory
fpath = os.path.join(output_dir, 'sub-' + bids_sub)
if not os.path.exists(fpath):
    print("Creating subject directory: " + fpath)
    os.mkdir(fpath)
else:
    print("Putting data in existing subject directory: " + fpath)

# Make a session directory
sess_path = os.path.join(os.path.join(output_dir, 'sub-' + bids_sub, 'ses-' + sess))
if not os.path.exists(sess_path):
    print("Creating new session directory: " + sess_path)
    os.mkdir(sess_path)
else:
    print("Putting data in existing session directory: " + sess_path)

# ==============================================================================
# Copy individual scans into relevant locations, in BIDS format
# ==============================================================================
# Put the Anatomical Scans to BIDS format
copy_to_bids(anat_runs, "anat", sess_path)
copy_to_bids(fmap_runs, "fmap", sess_path, fmap_apply_names)
copy_to_bids(func_runs, "func", sess_path)
copy_to_bids(dwi_runs, "dwi", sess_path)

print("SUCCESS! unpack_to_bids.py complete.\n----We recommend that you run this directory through a BIDS validator to ensure proper formatting (Just in case!)")

# NEEDSWORK: Add BIDS validator?
# NEEDSWORK: Handle event files (stim timing?)



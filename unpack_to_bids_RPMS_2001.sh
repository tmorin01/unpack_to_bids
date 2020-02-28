#!/bin/bash

# Test unpack_to_bids.sh

input_subj=RPMS_2001
subj=RPMS2001
sess=1

python unpack_to_bids.py --sub ${subj} \
               -i /projectnb/sternlab/tom/RPMS/raw_data/${input_subj}/${input_subj}/scans \
               -o /projectnb/sternlab/tom/RPMS/BIDS/ \
               -p "1-Dimensional Ravens Progressive Matrices Task" \
               --change "1.0.2" "Add RPMS_2001" \
               --sess ${sess} \
               --anat 8 sub-${subj}_ses-${sess}_T1w \
               --fmap 11 sub-${subj}_ses-${sess}_dir-AP_epi \
               --fmap 12 sub-${subj}_ses-${sess}_dir-PA_epi \
               --func 18 sub-${subj}_ses-${sess}_task-rest_run-1_bold \
               --func 20 sub-${subj}_ses-${sess}_task-rest_run-2_bold \
               --func 22 sub-${subj}_ses-${sess}_task-ravens_run-1_bold \
               --func 24 sub-${subj}_ses-${sess}_task-ravens_run-2_bold \
               --func 26 sub-${subj}_ses-${sess}_task-ravens_run-3_bold \
               --func 28 sub-${subj}_ses-${sess}_task-ravens_run-4_bold \
               --func 30 sub-${subj}_ses-${sess}_task-ravens_run-5_bold \
               --func 32 sub-${subj}_ses-${sess}_task-ravens_run-6_bold


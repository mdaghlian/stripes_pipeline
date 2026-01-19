#!/usr/bin/env python
#$ -j Y
#$ -cwd
#$ -V

import os
import sys
import argparse
import warnings
import numpy as np
import nibabel as nib

warnings.filterwarnings('ignore')
opj = os.path.join

from dpu_mini.utils import dag_find_file_in_folder, dag_str2file
from dpu_mini.fs_tools import dag_load_nverts

# pybest use jurjens 
# git clone https://github.com/gjheij/pybest.git
# python setup.py develop


deriv_dir = '/Users/marcusdaghlian/CVL Dropbox/Marcus  Daghlian/pilot-clean/derivatives/'
fmriprep_dir = opj(deriv_dir, 'BIDS', 'derivatives', 'fmriprep')
pybest_dir = opj(deriv_dir, 'BIDS', 'derivatives', 'pybest')


sub = 'sub-01'
sfmp_dir = opj(fmriprep_dir, sub)
spyb_dir = opj(pybest_dir, sub)

# [1] Find bold files 
bold_files = dag_find_file_in_folder(
    ['colbw', '.nii', 'preproc_bold'], 
    sfmp_dir, 
    recursive=True, 

)

spybpreZ_dir = opj(spyb_dir, 'preZ')
if not os.path.exists(spybpreZ_dir):
    os.makedirs(spybpreZ_dir)
# For unzscoring... 
for f in bold_files: 
    # Need to save the mean, and the std
    tbase_name = f.split('_desc')[0]
    tbase_name = tbase_name.split('/')[-1]

    tdata = nib.load(f).get_fdata()

    tmean = np.mean(tdata, axis=-1) # mean over time 
    tstd = np.std(tdata, axis=-1)

    np.save(f'{tbase_name}_mean.npy', tmean)
    np.save(f'{tbase_name}_std.npy', tstd)

# Now run pybest 
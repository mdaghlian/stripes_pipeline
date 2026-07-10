import os,shutil,subprocess,glob,sys,json
opj = os.path.join
from pathlib import Path
import nibabel as nib
import numpy as np
from cvl_utils.preproc_func import run_cmd, set_project
import scipy.io as sio
set_project('stripes')

fsl_fs_docker='ndock_fsl_freesurfer:latest'
BIDS_DIR=os.environ['BIDS_DIR']
env = dict(
    BIDS_DIR=os.environ['BIDS_DIR'],
    SUBJECTS_DIR=os.environ['SUBJECTS_DIR'],
)


def dm_from_path(dm_path, tn_trs, t_tr, dur=30):
    tdm_mat = sio.loadmat(dm_path)
    dm_conds = [str(i[0]) for i in tdm_mat['names'][0]]
    ons = {}
    dur = {}
    cond_list = []
    for iC,c in enumerate(dm_conds):
        ons[c] = tdm_mat['onsets'][0][iC][0] # weird matlab... have to index this way
        print(ons[c])
        ons[c] = [int(i / t_tr) for i in ons[c]]
        print(ons[c])
        dur[c] = tdm_mat['durations'][0][iC][0] #int(tdm_mat['durations'][0][iC][0] // t_tr) # in trs
        if c != 'rest':
            cond_list.append(c)
    dmatrix = np.zeros((tn_trs, len(cond_list)))
    for iC,c in enumerate(cond_list):
        for tonset in ons[c]:
            dmatrix[tonset,iC] = 1.0


    t_dmatrix_info = {
        'dur' : dur, 
        'cond_list' : cond_list, 
        'ons' : ons,
        'dmatrix' : dmatrix, 
    }

    bw_vals = [(v, 'bw', i) for i, v in enumerate(ons['bw'])]
    col_vals = [(v, 'colour', i) for i, v in enumerate(ons['colour'])]

    all_vals = sorted(bw_vals + col_vals, key=lambda x: x[0])

    bw_order = [None] * len(ons['bw'])
    col_order = [None] * len(ons['colour'])

    for rank, (val, source, original_idx) in enumerate(all_vals):
        if source == 'bw':
            bw_order[original_idx] = rank
        else:
            col_order[original_idx] = rank

    beta_order = {'bw': bw_order, 'col': col_order}
    return t_dmatrix_info, beta_order


def mean_betas_from_runs(betas, nruns, beta_order,):
    ''' Extract from glm single outputs
    Assuming you ran a glm, with:
    - nruns
    - each run has a certain number of "trials" i.e., entries of 
    "1" in the design matrix
    - then the output array of betas from glm single will be:
        x, y, z, total-number-of-trials  

    The dictionary "beta_order", gives the order of trials,
    per condition. 
    beta_order = {
        'bw' : [1,2,4,7]
        'col': [0,3,5,6],
    }
    the 0th trial is "col", and the 1st "bw", 2nd "bw", 3rd="col"...

    This tells us, out of the last dmension of the glm-single betas, 
    which ones we want to average.   

    In my glm - the runs have identical beta_order, so I don't need to change anything
    But I do need to chop it up by the number of runs...
    '''

    # array along final axis, into the different runs
    tbsplit = np.array_split(betas, nruns, axis=-1)

    betas_full = {}
    for k in beta_order.keys():
        # for this condition...
        for iR in range(nruns):
            # take all of the trials matching this condition
            # - for each run 
            for ibeta in beta_order[k]:
                betas_full[k].append(tbsplit[iR][:,:,:,ibeta])
        # average them over everything...
        # we could be more sophisticated later and do Rsq? 
        betas_full[k] = np.nanmean(betas_full[k], axis=0)
    
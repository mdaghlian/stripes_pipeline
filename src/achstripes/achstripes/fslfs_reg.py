import os,shutil,subprocess,glob,sys,json
opj = os.path.join
from pathlib import Path
import nibabel as nib
import numpy as np
from cvl_utils.preproc_func import run_cmd, set_project
set_project('stripes')

fsl_fs_docker='ndock_fsl_freesurfer:latest'
BIDS_DIR=os.environ['BIDS_DIR']
env = dict(
    BIDS_DIR=os.environ['BIDS_DIR'],
    SUBJECTS_DIR=os.environ['SUBJECTS_DIR'],
)



def fslfs_reg(sub, anat_ref, func_ref, reg_dir):
    run_cmd(
        ['fslreorient2std', func_ref, func_ref],
        env_vars=env,
        work_dir=BIDS_DIR,
        docker_image=fsl_fs_docker,
    )    
    if not os.path.exists(reg_dir):
        os.makedirs(reg_dir)
    reg_dat = opj(reg_dir, 'bbreg.dat')
    fsl_mat = opj(reg_dir, 'bbreg.mat')
    reg_lta = opj(reg_dir, 'bbreg.lta')
    if not os.path.exists(opj(reg_dir, 'rmFlirtInit.nii.gz')):
        # Flirt first 
        run_cmd(
            ['flirt', '-in', func_ref, 
            '-ref', anat_ref, '-omat', opj(reg_dir, 'rmFlirtInit.mat'),
            '-out', opj(reg_dir, 'rmFlirtInit.nii.gz'),
            '-dof', '12', '-cost', 'mutualinfo', 
            ],
            env_vars=env,
            work_dir=BIDS_DIR,
            docker_image=fsl_fs_docker,
        )
    if not os.path.exists(opj(reg_dir, 'rmFlirtInit.dat')):
        # Tkregister
        run_cmd(
            [f'tkregister2', '--s', sub,
            '--mov', func_ref,
            '--targ', anat_ref,
            '--fsl', opj(reg_dir, 'rmFlirtInit.mat'),
            '--reg', opj(reg_dir, 'rmFlirtInit.dat'),
            '--noedit'],    
            docker_image=fsl_fs_docker,
            work_dir=BIDS_DIR,
            env_vars=env,
        )
    if not os.path.exists(reg_dat):
        run_cmd(
            [
            'bbregister',
            '--s', sub,
            '--mov', func_ref,
            '--reg', reg_dat,
            '--fslmat', fsl_mat,
            '--bold', '--init-fsl'
            ],
            env_vars=env,
            docker_image='local',
            work_dir=BIDS_DIR,
        )


def fslfs_func2anat(func, sub, reg_dir, interp='trilin'):
    run_cmd(
        ['fslreorient2std', func, func],
        env_vars=env,
        work_dir=BIDS_DIR,
        docker_image=fsl_fs_docker,
    )
    reg_lta = opj(reg_dir, 'tmp.lta')
    reg_dat = opj(reg_dir,'bbreg.dat')
    out = func.replace('.nii.gz', 'al.nii.gz')
    run_cmd(
        [
            'tkregister2',
            '--mov', func,
            '--reg', reg_dat,
            '--targ', opj(env['SUBJECTS_DIR'], sub, 'mri', 'brain.mgz'),
            '--ltaout', reg_lta,
        ],
        env_vars=env,
        work_dir=BIDS_DIR,
        docker_image='local',
    )

    run_cmd(
        [
            'mri_vol2vol',
            '--mov', func,
            '--targ', opj(env['SUBJECTS_DIR'], sub, 'mri', 'brain.mgz'),
            '--lta', reg_lta,
            '--interp', interp,
            '--o', out,
        ],
        env_vars=env,
        work_dir=BIDS_DIR,
        docker_image='local',
    )

def fslfs_func2anat_vals(func_array, sub, reg_dir, func_ref, interp='trilin'):
    # find reference func file to copy header from
    rnib_ref = nib.load(func_ref)
    # create a temporary file for the input func array
    temp_func_file = opj(reg_dir, 'temp_func.nii.gz')

    temp_func_img = nib.Nifti1Image(
        func_array.astype(np.float32), affine=rnib_ref.affine, ) #header=func_ref_img.header)
    nib.save(temp_func_img, temp_func_file)
    fslfs_func2anat(temp_func_file,sub, reg_dir, interp=interp)
    out_nib = nib.load(temp_func_file.replace('.nii.gz', 'al.nii.gz'))
    out_data = out_nib.get_fdata()
    os.unlink(temp_func_file)
    os.unlink(temp_func_file.replace('.nii.gz', 'al.nii.gz'))
    return out_data



def fslfs_func2surf(func, sub, reg_dir, interp='trilin', hemi_list=['lh', 'rh'], proj_str=['--projcfrac-avg', '0.2', '0.8', '0.1']):
    run_cmd(
        ['fslreorient2std', func, func],
        env_vars=env,
        work_dir=BIDS_DIR,
        docker_image=fsl_fs_docker,
    )
    reg_lta = opj(reg_dir, 'tmp.lta')
    reg_dat = opj(reg_dir, 'bbreg.dat')
    # First register func -> anat (same as func2anat)
    run_cmd(
        [
            'tkregister2',
            '--mov', func,
            '--reg', reg_dat,
            '--targ', opj(env['SUBJECTS_DIR'], sub, 'mri', 'brain.mgz'),
            '--ltaout', reg_lta,
        ],
        env_vars=env,
        work_dir=BIDS_DIR,
        docker_image='local',
    )

    out_files = {}
    for hemi in hemi_list:
        out = func.replace('.nii.gz', f'_{hemi}_surf.mgh')
        run_cmd(
            [
                'mri_vol2surf',
                '--mov', func,
                '--reg', reg_lta,
                '--hemi', hemi,
                '--interp', interp,
                *proj_str, 
                '--o', out,
                '--cortex',
            ],
            env_vars=env,
            work_dir=BIDS_DIR,
            docker_image='local',
        )
        out_files[hemi] = out

    return out_files


def fslfs_func2surf_vals(func_array, sub, reg_dir, func_ref, interp='trilin', hemi_list=['lh', 'rh'], proj_str=['--projcfrac-avg', '0.2', '0.8', '0.1']):
    # Find reference func file to copy header/affine from
    rnib_ref = nib.load(func_ref)

    # Create a temporary file for the input func array
    temp_func_file = opj(reg_dir, 'temp_func.nii.gz')
    temp_func_img = nib.Nifti1Image(
        func_array.astype(np.float32), affine=rnib_ref.affine,
    )
    nib.save(temp_func_img, temp_func_file)

    # Project to surface for each hemisphere
    out_files = fslfs_func2surf(temp_func_file, sub, reg_dir, interp=interp, hemi_list=hemi_list,proj_str=proj_str)

    # Load and concatenate surface data across hemispheres -> shape (n_vx,)
    hemi_arrays = []
    for hemi in hemi_list:
        surf_nib = nib.load(out_files[hemi])
        surf_data = surf_nib.get_fdata().squeeze()  # (n_vx_hemi,) or (n_vx_hemi, n_tp)
        hemi_arrays.append(surf_data)

    out_data = np.concatenate(hemi_arrays, axis=0)  # (n_vx_total,)

    os.unlink(temp_func_file)
    os.unlink(out_files['lh'])
    os.unlink(out_files['rh'])

    return out_data
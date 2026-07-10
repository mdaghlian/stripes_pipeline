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

def load_spm_aligned(moco_folder):
    """
    Load SPM aligned data from the moco_folder.
    Args:
        moco_folder (str): Path to the folder containing SPM aligned data.
    Returns:
        list : list of file paths
    """
    rfiles_ = os.listdir(
        moco_folder
    )
    rfiles = [opj(moco_folder,f) for f in rfiles_ if (f.endswith('bold.nii') and f.startswith('rsub')) ]
    rfiles = [f for f in rfiles if 'accordion' not in f]
    rfiles.sort()
    return rfiles


def split_half_from_nii_list(nii_list, output_dir, run_time_s=None):
    if len(nii_list)<2:
        print('not neough runs for split-half correlation')
        return
    all_data = []
    for iR,nii_path in enumerate(nii_list):
        img = nib.load(nii_path)
        data = img.get_fdata()
        if data.ndim != 4:
            raise ValueError(f"{nii_path} is not a 4D NIfTI file.")
        if run_time_s is not None:
            TR = img.header.get_zooms()[-1]
            print(f"Run {iR:02}: TR={TR:.2f}s, expected time points={run_time_s/TR:.1f}, actual time points={data.shape[-1]}")
            print(f"Chopping volumes after {run_time_s} seconds...")
            max_vols = int(run_time_s / TR)
            print(f"Keeping first {max_vols} volumes.")
            data = data[..., :max_vols]
        all_data.append(data)

    odd_runs = all_data[0::2]   # runs 0,2,4,... (1st,3rd,5th in human terms)
    even_runs = all_data[1::2]  # runs 1,3,5,...

    # Check shapes match
    ref_shape = all_data[0].shape
    for i, d in enumerate(all_data):
        if d.shape != ref_shape:
            raise ValueError(
                f"Run {i} has shape {d.shape}, expected {ref_shape}. "
                "All runs must have the same shape for split-half correlation."
            )
        
    # Average odd and even runs separately
    odd_mean = np.mean(np.stack(odd_runs, axis=0), axis=0)   # shape: X,Y,Z,T
    even_mean = np.mean(np.stack(even_runs, axis=0), axis=0) # shape: X,Y,Z,T

    # Voxelwise correlation across time
    odd_centered = odd_mean - np.mean(odd_mean, axis=-1, keepdims=True)
    even_centered = even_mean - np.mean(even_mean, axis=-1, keepdims=True)

    numerator = np.sum(odd_centered * even_centered, axis=-1)
    odd_denom = np.sqrt(np.sum(odd_centered ** 2, axis=-1))
    even_denom = np.sqrt(np.sum(even_centered ** 2, axis=-1))
    denominator = odd_denom * even_denom

    split_half_corr = np.full(numerator.shape, np.nan, dtype=np.float64)
    valid = denominator > 0
    split_half_corr[valid] = numerator[valid] / denominator[valid]

    # Clip tiny floating-point overshoots
    split_half_corr = np.clip(split_half_corr, -1, 1)

    corr_img = nib.Nifti1Image(split_half_corr, affine=img.affine, header=img.header)
    out_path = os.path.join(output_dir, "rSPLITHALF_corr.nii.gz")
    nib.save(corr_img, out_path)

    print(f"Saved split-half correlation map: {out_path}")
    print(f"Mean split-half correlation: {np.nanmean(split_half_corr):.4f}")

def tsnr_from_nii_list(nii_list, output_dir, run_time_s=None):
    nii_ref = nib.load(nii_list[0])
    all_tsnr = []
    for iR,nii_path in enumerate(nii_list):
        all_tsnr.append(
            tsnr_from_nii(
                nii_path    =   nii_path, 
                out_path    =   opj(output_dir, f"r{iR:02}_tsnr.nii.gz"),
                run_time_s  =   run_time_s)
                )
    
    overall_mean = np.nanmean(all_tsnr, axis=0)
    tsnr_img = nib.Nifti1Image(overall_mean, affine=nii_ref.affine, header=nii_ref.header)
    out_path = os.path.join(output_dir, "rMEAN_tsnr.nii.gz")
    nib.save(tsnr_img, out_path)
    print(f"Saved mean tSNR map: {out_path}")

    return overall_mean

def tsnr_from_nii(nii_path, out_path, run_time_s=None):
    """
    Calculate the temporal signal-to-noise ratio (tSNR) from a NIfTI file.
    Args:
        nii_file (str): Path to the NIfTI file.
        output_dir (str): Path to the output directory.
        run_time_s (float): The total run time in seconds.
        TR_s (float): The repetition time in seconds.
    Returns:
        float: The calculated tSNR.
    """
    
    img = nib.load(nii_path) # load 
    data = img.get_fdata()
    if data.ndim != 4:
        raise ValueError(f"{nii_path} is not a 4D NIfTI file.")
    TR = img.header.get_zooms()[-1]
    print(TR)
    print(f"Run {os.path.basename(nii_path)}: TR={TR:.2f}s, time points={data.shape[-1]}")
    if run_time_s is not None:
        print(f"Chopping volumes after {run_time_s} seconds...")
        max_vols = int(run_time_s / TR)
        print(f"Keeping first {max_vols} volumes.")
        data = data[..., :max_vols]

    # Compute mean and std across time axis (last dimension)
    mean_img = np.mean(data, axis=-1)
    std_img = np.std(data, axis=-1)

    # Avoid division by zero
    std_img[std_img == 0] = np.nan
    tsnr = mean_img / std_img

    # Save tSNR map
    tsnr_img = nib.Nifti1Image(tsnr, affine=img.affine, header=img.header)
    nib.save(tsnr_img, out_path)

    print(f"Saved tSNR map: {out_path}")
    return tsnr




def add_ref_anat_and_vol_rois(sub, fs_dir, output_dir,):
    ''' Add a reference anatomy + ROIs to the folder of interest
    [1] Copy the FS anatomy (change to nifti)
    [2] Make B14 All volume ROI + dilate it
    [3] Make B14 V2 volume ROI + dilated it 
    '''
    env = dict(
        BIDS_DIR=os.environ['BIDS_DIR'],
        SUBEJCTS_DIR=os.environ['SUBJECTS_DIR']
    )
    ndil = 2
    # [1] ...
    #     shutil.rmtree(stest_dir, )
    fs_anat = opj(fs_dir, sub, 'mri', 'brain.mgz')
    anat_ref = opj(output_dir, 'anat_ref.nii.gz')
    # Add the brain as anatomical ref
    if not os.path.exists(anat_ref):
        run_cmd(
            ['mri_convert', fs_anat, anat_ref],
            env_vars=env,
            work_dir=BIDS_DIR,
            docker_image=fsl_fs_docker,
        )

    # Add the ROIs
    b14_vol = opj(output_dir, 'b14_vol.nii.gz')
    b14_vol_dil = opj(output_dir, f'b14_vol{ndil}.nii.gz')
    if not os.path.exists(b14_vol):
        cmd = ' '.join([
            f"mri_label2vol --temp {opj(fs_dir, sub, 'mri', 'orig.mgz')} ",
            f"--label lh.b14_V1.label --label rh.b14_V1.label "
            f"--label lh.b14_V2.label --label rh.b14_V2.label ",
            f"--label lh.b14_V3.label --label rh.b14_V3.label ",
            f"--o {b14_vol} --identity" ])
        subprocess.run(cmd, shell=True, check=True, cwd=opj(fs_dir, sub, 'label', 'custom'))
        # Dilate to cover a bit more
        cmd = [
            'fslmaths', b14_vol, *['-dilM'] * ndil, '-bin', b14_vol_dil
        ]
        run_cmd(
            cmd,
            env_vars=env,
            work_dir=BIDS_DIR,
            docker_image=fsl_fs_docker,
        )

    b14_v2 = opj(output_dir, 'b14_v2.nii.gz')
    b14_v2_dil = opj(output_dir, f'b14_v2{ndil}.nii.gz')
    if not os.path.exists(b14_v2):
        # Add the ROIs
        cmd = ' '.join([
            f"mri_label2vol --temp {opj(fs_dir, sub, 'mri', 'orig.mgz')} ",
            f"--label lh.b14_V2.label --label rh.b14_V2.label ",
            f"--o {b14_v2} --identity" ])
        subprocess.run(cmd, shell=True, check=True, cwd=opj(fs_dir, sub, 'label', 'custom'))
        # Dilate to cover a bit more
        cmd = [
            'fslmaths', b14_v2, *['-dilM'] * ndil, '-bin', b14_v2_dil
        ]

        run_cmd(
            cmd,
            env_vars=env,
            work_dir=BIDS_DIR,
            docker_image=fsl_fs_docker,
        )
    b14_hv4 = opj(output_dir, 'b14_hv4.nii.gz')
    b14_hv4_dil = opj(output_dir, f'b14_hv4{ndil}.nii.gz')
    if not os.path.exists(b14_hv4):
        # Add the ROIs
        cmd = ' '.join([
            f"mri_label2vol --temp {opj(fs_dir, sub, 'mri', 'orig.mgz')} ",
            f"--label lh.b14_hV4.label --label rh.b14_hV4.label ",
            f"--o {b14_hv4} --identity" ])
        subprocess.run(cmd, shell=True, check=True, cwd=opj(fs_dir, sub, 'label', 'custom'))
        # Dilate to cover a bit more
        cmd = [
            'fslmaths', b14_hv4, *['-dilM'] * ndil, '-bin', b14_hv4_dil
        ]

        run_cmd(
            cmd,
            env_vars=env,
            work_dir=BIDS_DIR,
            docker_image=fsl_fs_docker,
        )


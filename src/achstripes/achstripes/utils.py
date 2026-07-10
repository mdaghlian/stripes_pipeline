import os,shutil,subprocess,glob,sys,json
opj = os.path.join
from pathlib import Path
import nibabel as nib
import numpy as np


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
    print(f"Run {os.path.basename(nii_path)}: TR={TR:.2f}s, expected time points={run_time_s/TR:.1f}, actual time points={data.shape[-1]}")
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

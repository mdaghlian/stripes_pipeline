import argparse
import numpy as np
import nibabel as nib
from nilearn import masking, image
import os 
opj = os.path.join
from pathlib import Path
deriv_dir = '/Users/marcusdaghlian/CVL Dropbox/Marcus  Daghlian/pilot-clean/derivatives'

def prepare_for_freesurfer(img_data, mask_data):
    """Scale image to FreeSurfer-friendly range"""
    # Shift from [-0.5, 0.5] to [0, 1]
    scaled = img_data + 0.5
    
    # Apply mask
    scaled[mask_data == 0] = 0
    
    # Scale to 0-4095 range (12-bit, common for MP2RAGE)
    scaled = scaled * 4095
    
    # Clip to valid range
    scaled = np.clip(scaled, 0, 4095)
    
    return scaled.astype(np.float32)

def run_pipeline(args):
    sub = args.sub
    mp2rage_dir = opj(deriv_dir, 'MP2RAGE_source', sub)
    output_file = opj(mp2rage_dir, 'uni_masked_by_inv2')
    if not os.path.exists(output_file):
        os.makedirs(output_file)
    output_path = opj(output_file, f'{sub}_MP2RAGE_uni_inv2_masked.nii')
    
    # Find uni
    uni = opj(mp2rage_dir, f'{sub}_MP2RAGE_uni.nii')
    inv2 = opj(mp2rage_dir, 'presurf_biascorrect', f'{sub}_MP2RAGE_inv2_biascorrected.nii')
    inv2 = nib.load(inv2)
    uni_img = nib.load(uni)
    uni_data = uni_img.get_fdata()
    # Rescale -0.5 -> 0.5
    if np.min(uni_data) >= 0:
        uni_data = uni_data / np.max(uni_data) - 0.5
    print("--- Masking ---")
    mask_img = masking.compute_background_mask(
        image.threshold_img(inv2, args.threshold)
    )
    uni_data[mask_img.get_fdata() == 0] = -0.5
    masked_img = nib.Nifti1Image(uni_data.astype(np.float32), uni_img.affine)
    final_data = masked_img.get_fdata()

    print("--- Preparing for FreeSurfer ---")
    final_data = prepare_for_freesurfer(final_data, mask_img.get_fdata())
    final_img = nib.Nifti1Image(final_data.astype(np.float32), masked_img.affine)
    nib.save(final_img, output_path)

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MP2RAGE Robust UNI Generation")
    parser.add_argument("--sub", required=True)
    parser.add_argument("--threshold", default="70%")
    run_pipeline(parser.parse_args())

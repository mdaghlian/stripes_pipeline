import argparse
import numpy as np
import nibabel as nib
import SimpleITK as sitk
from nilearn import masking, image


def calculate_standard_uni(inv1_data, inv2_data):
    denom = inv1_data**2 + inv2_data**2
    uni = np.divide(
        inv1_data * inv2_data,
        denom,
        out=np.zeros_like(denom),
        where=denom != 0,
    )
    return uni


def robust_combine(inv1_img, inv2_img, uni_data, factor):
    inv1_data = inv1_img.get_fdata()
    inv2_data = inv2_img.get_fdata()

    inv1_data = np.sign(uni_data) * inv1_data

    a = -uni_data
    b = inv2_data
    c = -inv2_data**2 * uni_data

    delta = np.sqrt(np.maximum(b**2 - 4 * a * c, 0))

    safe_a = 2 * a
    root_pos = np.divide(-b + delta, safe_a, out=np.zeros_like(a), where=np.abs(safe_a) > 1e-10)
    root_neg = np.divide(-b - delta, safe_a, out=np.zeros_like(a), where=np.abs(safe_a) > 1e-10)

    mask_neg = np.abs(inv1_data - root_pos) > np.abs(inv1_data - root_neg)
    inv1_final = np.where(mask_neg, root_neg, root_pos)

    noise_region = inv2_data[1:, -10:, -10:]
    if noise_region.size == 0:
        beta = (factor * np.mean(inv2_data) * 0.1) ** 2
    else:
        beta = (factor * np.mean(noise_region)) ** 2

    combined = (
        inv1_final * inv2_data - beta
    ) / (inv1_final**2 + inv2_data**2 + 2 * beta)

    combined = np.nan_to_num(combined, nan=0.0, posinf=0.5, neginf=-0.5)

    return nib.Nifti1Image(combined.astype(np.float32), inv1_img.affine)


def n4_bias_correct(nifti_img, mask_img):
    data = nifti_img.get_fdata().astype(np.float32)
    mask = mask_img.get_fdata() > 0

    sitk_img = sitk.GetImageFromArray(data)
    sitk_img = sitk.Cast(sitk_img, sitk.sitkFloat32)

    sitk_mask = sitk.GetImageFromArray(mask.astype(np.uint8))

    corrector = sitk.N4BiasFieldCorrectionImageFilter()
    corrector.SetMaximumNumberOfIterations([50, 50, 50, 50])
    corrector.SetConvergenceThreshold(1e-6)

    corrected = corrector.Execute(sitk_img, sitk_mask)

    corrected_np = sitk.GetArrayFromImage(corrected)
    return nib.Nifti1Image(corrected_np, nifti_img.affine)


def run_pipeline(args):
    print("--- Loading INV1 and INV2 ---")
    inv1 = nib.load(args.inv1)
    inv2 = nib.load(args.inv2)

    if inv1.shape != inv2.shape:
        raise ValueError("INV1 and INV2 must have the same dimensions")

    inv1_data = inv1.get_fdata()
    inv2_data = inv2.get_fdata()
    if args.bias_correct_inv2:
        print("--- N4 Bias Correction of INV2 ---")
        # Create mask from INV2
        inv2_mask = masking.compute_background_mask(
            image.threshold_img(inv2, args.threshold)
        )
        
        inv2_corrected = n4_bias_correct(inv2, inv2_mask)
        inv2 = inv2_corrected  # Use corrected version
        inv2_data = inv2.get_fdata()
        print("INV2 bias correction complete")

    if args.uni:
        print("--- Using provided UNI ---")
        uni_data = nib.load(args.uni).get_fdata()
        if np.min(uni_data) >= 0:
            uni_data = uni_data / np.max(uni_data) - 0.5
    else:
        print("--- Generating UNI ---")
        uni_data = calculate_standard_uni(inv1_data, inv2_data)

    print("--- Robust combination ---")
    combined_img = robust_combine(inv1, inv2, uni_data, args.factor)
    combined_data = combined_img.get_fdata()

    print("--- Masking ---")
    mask_img = masking.compute_background_mask(
        image.threshold_img(inv2, args.threshold)
    )

    combined_data[mask_img.get_fdata() == 0] = -0.5
    masked_img = nib.Nifti1Image(combined_data.astype(np.float32), combined_img.affine)

    if args.bias_correct and not args.bias_correct_inv2:
        print("--- N4 Bias Field Correction (SimpleITK) ---")
        shifted = masked_img.get_fdata() + 0.5
        shifted_img = nib.Nifti1Image(shifted.astype(np.float32), masked_img.affine)

        corrected = n4_bias_correct(shifted_img, mask_img)

        final_data = corrected.get_fdata() - 0.5
    else:
        final_data = masked_img.get_fdata()

    print("--- Preparing for FreeSurfer ---")
    final_data = prepare_for_freesurfer(final_data, mask_img.get_fdata())
    final_img = nib.Nifti1Image(final_data.astype(np.float32), masked_img.affine)
    nib.save(final_img, args.output_uni)

    print(f"Saved: {args.output_uni}")
    print(f"Final range: [{final_img.get_fdata().min():.3f}, {final_img.get_fdata().max():.3f}]")

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MP2RAGE Robust UNI Generation")
    parser.add_argument("--inv1", required=True)
    parser.add_argument("--inv2", required=True)
    parser.add_argument("--uni")
    parser.add_argument("--output_uni", default="robust_uni.nii.gz")
    parser.add_argument("--factor", type=float, default=2.0)
    parser.add_argument("--threshold", default="70%")
    parser.add_argument("--bias-correct-inv2", action="store_true",
                    help="Apply N4 bias correction to INV2 before combination")
    parser.add_argument("--bias-correct", action="store_true",
                    help="Apply N4 bias correction to final combined image")

    run_pipeline(parser.parse_args())

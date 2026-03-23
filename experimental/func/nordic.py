#!/usr/bin/env python3
"""
run_nordic.py

Apply NORDIC denoising to all EPI NIfTI files in an input folder.

Usage:
    python run_nordic.py <input_folder> <output_folder>
                        --nordic-path /path/to/NORDIC_Raw
                        [--matlab-path /usr/local/MATLAB/R2023b/bin/matlab]
                        [--factor-error 1.0]
                        [--overwrite]

Assumptions:
    - Magnitude-only data (no phase images)
    - No appended noise volumes
    - Flat folder structure (one NIfTI per run)
    - NIFTI_NORDIC toolbox available (Moeller et al., Minnesota)

NIFTI_NORDIC signature:
    NIFTI_NORDIC(fn_magn_in, fn_phase_in, fn_out, ARG)
    - fn_magn_in  : full path to input magnitude NIfTI
    - fn_phase_in : ignored when ARG.magnitude_only=1, but must be passed
    - fn_out      : output stem (no extension, no directory); written to ARG.DIROUT
    - ARG         : options struct
"""

import argparse
import subprocess
import sys
from pathlib import Path


def build_matlab_cmd(
    in_path: Path,
    out_stem: str,
    out_dir: Path,
    nordic_path: Path,
    factor_error: float,
    matlab_exe: str,
) -> list[str]:
    """
    Build the MATLAB -batch command to call NIFTI_NORDIC.

    Key ARG fields for magnitude-only fMRI:
      magnitude_only=1     : ignore phase input, magnitude Rician mode
      temporal_phase=1     : standard fMRI slice/time phase correction
      noise_volume_last=0  : no appended noise volumes
      factor_error         : threshold scaling (1.0 = default)
      save_gfactor_map=1   : write relative gfactor map for QC
      DIROUT               : output directory (trailing slash required by toolbox)
    """
    in_str      = str(in_path).replace("'", "''")
    out_dir_str = str(out_dir).replace("'", "''")

    matlab_script = (
        f"addpath(genpath('{str(nordic_path)}'));"
        f"ARG.magnitude_only=1;"
        f"ARG.temporal_phase=1;"
        f"ARG.noise_volume_last=0;"
        f"ARG.factor_error={factor_error};"
        f"ARG.save_gfactor_map=1;"
        f"ARG.DIROUT='{out_dir_str}/';"
        f"NIFTI_NORDIC('{in_str}', '{in_str}', '{out_stem}', ARG);"
        f"exit;"
    )

    return [matlab_exe, "-nodisplay", "-nosplash", "-batch", matlab_script]


def _check_skip(out_path: Path, overwrite: bool) -> bool:
    """Return True if this file should be skipped."""
    if out_path.exists():
        if overwrite:
            print(f"  [overwrite] {out_path.name}")
            return False
        else:
            print(f"  [skip]      {out_path.name} (already exists, use --overwrite to redo)")
            return True
    print(f"  [run]       {out_path.name}")
    return False


def run_nordic(
    input_folder: Path,
    output_folder: Path,
    matlab_exe: str,
    nordic_path: Path,
    factor_error: float,
    overwrite: bool,
) -> None:

    output_folder.mkdir(parents=True, exist_ok=True)

    epi_files = sorted(input_folder.glob("*.nii")) + sorted(input_folder.glob("*.nii.gz"))

    if not epi_files:
        print(f"No NIfTI files found in {input_folder}")
        sys.exit(1)

    print(f"\nFound {len(epi_files)} EPI file(s) in {input_folder}")
    print(f"Output folder : {output_folder}")
    print(f"factor_error  : {factor_error}\n")

    failed = []

    for epi in epi_files:
        # Build output stem (no extension) and expected output path.
        # NIFTI_NORDIC writes {DIROUT}{stem}.nii (always uncompressed).
        if epi.name.endswith(".nii.gz"):
            stem_orig = epi.name[:-7]
        else:
            stem_orig = epi.stem

        out_stem = f"{stem_orig}_nordic"
        out_path = output_folder / f"{out_stem}.nii"

        if _check_skip(out_path, overwrite):
            continue

        cmd = build_matlab_cmd(
            in_path=epi,
            out_stem=out_stem,
            out_dir=output_folder,
            nordic_path=nordic_path,
            factor_error=factor_error,
            matlab_exe=matlab_exe,
        )

        print(f"    Running NIFTI_NORDIC...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            # Print last few lines of MATLAB stdout (skip banner noise)
            if result.stdout:
                for line in result.stdout.strip().splitlines()[-15:]:
                    print(f"    {line}")

            if not out_path.exists():
                raise FileNotFoundError(
                    f"NIFTI_NORDIC finished without error but expected output not found:\n"
                    f"  {out_path}\n"
                    f"Check DIROUT and fn_out stem handling."
                )

            print(f"    Done -> {out_path.name}\n")

        except subprocess.CalledProcessError as e:
            print(f"  [ERROR] NIFTI_NORDIC failed for {epi.name}")
            if e.stderr:
                print(f"    STDERR (last 500 chars):\n    {e.stderr[-500:]}")
            failed.append(epi.name)

        except FileNotFoundError as e:
            print(f"  [ERROR] {e}")
            failed.append(epi.name)

    # Summary
    n_done = len(epi_files) - len(failed)
    print(f"\n{'='*55}")
    print(f"NORDIC complete: {n_done}/{len(epi_files)} file(s) processed successfully.")
    if failed:
        print("Failed:")
        for f in failed:
            print(f"  - {f}")
    print(f"{'='*55}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Apply NIFTI_NORDIC denoising to all EPI NIfTIs in a folder."
    )
    parser.add_argument("input_folder",  type=Path, help="Folder containing EPI NIfTI files")
    parser.add_argument("output_folder", type=Path, help="Folder to write denoised outputs")
    parser.add_argument(
        "--matlab-path",
        type=str,
        default="matlab",
        help="Path to MATLAB executable (default: 'matlab', assumes it is on PATH)",
    )
    parser.add_argument(
        "--nordic-path",
        type=Path,
        required=True,
        help="Path to the NORDIC toolbox directory (added to MATLAB path recursively)",
    )
    parser.add_argument(
        "--factor-error",
        type=float,
        default=1.0,
        help=(
            "Threshold scaling factor (default: 1.0). "
            "Increase to e.g. 1.1 if you see ringing or patch artefacts in output."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Reprocess files even if output already exists",
    )

    args = parser.parse_args()

    if not args.input_folder.is_dir():
        print(f"Error: input folder does not exist: {args.input_folder}")
        sys.exit(1)

    if not args.nordic_path.is_dir():
        print(f"Error: NORDIC toolbox path does not exist: {args.nordic_path}")
        sys.exit(1)

    run_nordic(
        input_folder=args.input_folder,
        output_folder=args.output_folder,
        matlab_exe=args.matlab_path,
        nordic_path=args.nordic_path,
        factor_error=args.factor_error,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
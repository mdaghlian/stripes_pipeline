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


def fs_upsample_bold(img_in, img_out, factor, ow=False):    
    assert os.path.exists(img_in), f"{img_in} does not exist"
    if os.path.exists(img_out) & (not ow):
        print(f'{img_out} already exists, not overwriting')
        return
    if os.path.exists(img_out) &  ow:
        print(f'Overwriting {img_out}')
    
    img = nib.load(img_in)
    zooms = img.header.get_zooms()[:3]
    zooms = img.header.get_zooms()[:3]  # (vx, vy, vz), ignore 4th dim (time) if present
    new_zooms = [round(z / factor, 6) for z in zooms]
    print(f"Original voxel size: {zooms}")
    print(f"Target voxel size (factor={factor}x): {new_zooms}")
    run_cmd([
        'mri_convert', 
        '-vs', str(new_zooms[0]),str(new_zooms[1]), str(new_zooms[2]),
        '-rt', 'interpolate', img_in, img_out 
        ], 
        # env_vars=env, 
        docker_image='local',
        # work_dir=
    )    



def bref_bmask(bref):
    assert os.path.exists(bref), f"{bref} does not exist"
    bname = os.path.basename(bref).split('.nii')[0]
    pname = os.path.dirname(bref)
    out = opj(pname, f'{bname}_bet.nii.gz')
    out_mask = opj(pname, f'{bname}_bet_mask.nii.gz')
    if os.path.exists(out_mask):
        return out_mask
        
    run_cmd([
        'bet', bref, out, '-m', '-n', '-f', '0.3', '-R' 
        ], 
        env_vars=env, 
        docker_image=fsl_fs_docker,
        work_dir=os.path.dirname(bref)
    )   
    # dilate x3  
    run_cmd(
        ['fslmaths', out_mask, *['-dilM'] * 3, '-bin', out_mask],
        env_vars=env, 
        docker_image=fsl_fs_docker,
        work_dir=os.path.dirname(bref)
    )
    os.unlink(out)
    return out_mask

def fs_upsample_mesh(sub, subjects_dir=os.environ['SUBJECTS_DIR'], subdiv='4'):
    subdiv = str(subdiv)
    # [1] pial
    # mris_mesh_subdivide --surf $LH_PIAL_OG --out ${LH_PIAL_OG}.subdiv01 --method butterfly --iter 1
    for surf in ['pial', 'white', 'inflated', 'sphere']:
        for hemi in ['lh', 'rh']:
            og_mesh = opj(subjects_dir, sub, 'surf', f"{hemi}.{surf}")
            new_mesh = opj(subjects_dir, sub, 'surf', f"{hemi}.{surf}.subdiv{subdiv}")
            if not os.path.exists(new_mesh):
                print(new_mesh)
                run_cmd([
                    'mris_mesh_subdivide', '--surf', og_mesh, '--out', 
                    new_mesh, '--method', 'butterfly', '--iter', subdiv,],
                    # env_vars=env, 
                    docker_image='local',
                    # work_dir=os.path.dirname(bref)
                )
    



"""
sub-01 surface refinement + functional projection
====================================================

Part 1 (shell/FreeSurfer) is documented at the bottom of this file as
comments — run it first, outside Python.

Part 2 (this module) does:
  1. Load a native FreeSurfer surface (e.g. lh.white)
  2. Iteratively refine it with midpoint ("simple butterfly") subdivision
  3. Write each refined level back out in FreeSurfer binary surface format
     so FreeSurfer's own tools (mri_vol2surf) can use them directly
  4. Project a functional volume onto each refined surface with trilinear
     interpolation, and report the number of unique voxels sampled
"""

import os
import numpy as np
import nibabel as nib
from nibabel.freesurfer.io import read_geometry, write_geometry, write_morph_data
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree



# ----------------------------------------------------------------------
# 2. TRILINEAR PROJECTION OF FUNCTIONAL DATA ONTO A (REFINED) SURFACE
# ----------------------------------------------------------------------

def tkras_to_voxel_affine(func_img, reg_dat_path, t1_img):
    """
    Build the 4x4 matrix that maps FreeSurfer *surface* (tkreg) RAS
    coordinates directly to functional-volume voxel indices, i.e. the
    same chain mri_vol2surf uses internally:

        vox_func = inv(vox2ras_func) @ ras2ras_reg @ vox2ras_tkr_T1 @ [x,y,z,1]

    func_img      : nibabel image of the functional run (already loaded)
    reg_dat_path  : path to bbregister's register.dat (tkreg-style .dat,
                    produced by e.g. `bbregister --s sub-01 --mov func.nii.gz
                    --reg register.dat --bold`)
    t1_img        : nibabel image of the subject's mri/T1.mgz (or orig.mgz)
    """
    # tkreg (surface RAS) -> scanner RAS for the T1 the surfaces live in
    vox2ras_tkr_t1 = t1_img.header.get_vox2ras_tkr()
    vox2ras_t1 = t1_img.header.get_vox2ras()
    tkras2ras_t1 = vox2ras_t1 @ np.linalg.inv(vox2ras_tkr_t1)

    # register.dat: 4x4 tkreg-style matrix mapping T1 tkras -> func tkras
    reg = _read_register_dat(reg_dat_path)

    func_vox2ras_tkr = func_img.header.get_vox2ras_tkr()
    ras_tkr2vox_func = np.linalg.inv(func_vox2ras_tkr)

    # full chain: surface tkras (T1) -> func tkras -> func voxel
    return ras_tkr2vox_func @ reg @ tkras2ras_t1


def _read_register_dat(path):
    with open(path) as fh:
        lines = [l.strip() for l in fh if l.strip()]
    # lines: subject, in-plane res, slice thickness, intensity, then 4 rows of the matrix, then 'round'
    mat_lines = lines[4:8]
    mat = np.array([[float(x) for x in row.split()] for row in mat_lines])
    return mat


def project_volume_to_surface(func_path, vertices_tkras, affine_tkras2voxfunc,
                                frame=None):
    """
    Trilinearly sample a functional volume at each surface vertex.

    func_path            : path to functional nifti (3D or 4D)
    vertices_tkras        : (N,3) vertex coordinates in T1 tkreg RAS
    affine_tkras2voxfunc   : 4x4 from tkras_to_voxel_affine()
    frame                 : which timepoint to sample (None -> average over
                             all timepoints, matching a mean-functional projection)

    Returns:
      sampled_values : (N,) interpolated intensities (trilinear, order=1)
      voxel_idx      : (N,3) nearest-integer voxel index each vertex fell in
                        (used for the unique-voxel-count metric)
    """
    func_img = nib.load(func_path)
    data = func_img.get_fdata()
    if data.ndim == 4:
        data = data.mean(axis=3) if frame is None else data[..., frame]

    homog = np.concatenate([vertices_tkras, np.ones((len(vertices_tkras), 1))], axis=1)
    vox_coords = (affine_tkras2voxfunc @ homog.T).T[:, :3]   # (N,3) fractional voxel coords

    # map_coordinates wants (3, N) in (i, j, k) order = same as vox_coords columns
    sampled_values = map_coordinates(data, vox_coords.T, order=1, mode="nearest")

    voxel_idx = np.round(vox_coords).astype(int)
    return sampled_values, voxel_idx


def project_volume_to_surface_nn(func_path, vertices_tkras, affine_tkras2voxfunc,
                                   frame=None):
    """
    Nearest-neighbor sample a functional volume at each surface vertex
    (same setup as project_volume_to_surface, but no interpolation between
    voxels -- each vertex just takes the value of its closest voxel).

    func_path            : path to functional nifti (3D or 4D)
    vertices_tkras        : (N,3) vertex coordinates in T1 tkreg RAS
    affine_tkras2voxfunc   : 4x4 from tkras_to_voxel_affine()
    frame                 : which timepoint to sample (None -> average over
                             all timepoints, matching a mean-functional projection)

    Returns:
      sampled_values : (N,) nearest-neighbor intensities (order=0)
      voxel_idx      : (N,3) nearest-integer voxel index each vertex fell in
    """
    func_img = nib.load(func_path)
    data = func_img.get_fdata()
    if data.ndim == 4:
        data = data.mean(axis=3) if frame is None else data[..., frame]

    homog = np.concatenate([vertices_tkras, np.ones((len(vertices_tkras), 1))], axis=1)
    vox_coords = (affine_tkras2voxfunc @ homog.T).T[:, :3]   # (N,3) fractional voxel coords

    sampled_values = map_coordinates(data, vox_coords.T, order=0, mode="nearest")

    voxel_idx = np.round(vox_coords).astype(int)
    return sampled_values, voxel_idx


def count_unique_voxels(voxel_idx):
    return np.unique(voxel_idx, axis=0).shape[0]


def project_bool_to_upsampled_mesh(orig_mesh, upsampled_mesh, bool_values, out_path=None):
    """
    Project a boolean array defined on the vertices of a native mesh (e.g. lh.pial)
    onto the vertices of an upsampled/subdivided version of that same mesh
    (e.g. lh.pial.subdiv4, from fs_upsample_mesh), via nearest-neighbor lookup
    on vertex coordinates.

    orig_mesh      : path to the native FreeSurfer surface bool_values was defined on
    upsampled_mesh : path to the subdivided surface (shares orig_mesh's vertices as a subset)
    bool_values    : (N,) boolean/0-1 array, one value per orig_mesh vertex
    out_path       : if given, write the upsampled result as a FreeSurfer curv-format
                     overlay (e.g. lh.pial.subdiv4.stripe_mask) for viewing in freeview

    Returns (M,) boolean array, one value per upsampled_mesh vertex.
    """
    orig_verts, _ = read_geometry(orig_mesh)
    up_verts, _ = read_geometry(upsampled_mesh)
    bool_values = np.asarray(bool_values)
    assert bool_values.shape[0] == orig_verts.shape[0], (
        f"bool_values has {bool_values.shape[0]} entries, "
        f"expected {orig_verts.shape[0]} (orig_mesh vertex count)"
    )

    tree = cKDTree(orig_verts)
    _, nn_idx = tree.query(up_verts)
    up_bool_values = bool_values[nn_idx]

    if out_path is not None:
        write_morph_data(out_path, up_bool_values.astype(np.float32))

    return up_bool_values


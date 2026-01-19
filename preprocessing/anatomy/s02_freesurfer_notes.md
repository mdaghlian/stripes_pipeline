


# Run freesurfer on preprocessed MP2RAGE data

```bash
proj_path="/Users/marcusdaghlian/projects/dp-clean-link/pilot-clean"
export SUBJECTS_DIR=$proj_path/derivatives/freesurfer

recon-all -subjid sub-01  \
    -i $proj_path/MP2RAGE_source/sub-01/presurf_MPRAGEise/sub-01_MP2RAGE_uni_MPRAGEised.nii \
    -hires -all -parallel -openmp 8 

```
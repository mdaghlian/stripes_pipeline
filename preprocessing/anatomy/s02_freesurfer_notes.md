


# Run freesurfer on preprocessed MP2RAGE data

```bash
proj_path="/Users/marcusdaghlian/projects/pilot-clean-link"
export SUBJECTS_DIR=$proj_path/derivatives/freesurfer

recon-all -subjid sub-03pesurfbc  \
    -i /Users/marcusdaghlian/projects/pilot-clean-link/derivatives/MP2RAGE_preprocess/sub-03/presurf_biascorrect/sub-03_acq-MP2RAGE_UNI_MPRAGEised_biascorrected.nii \
    -hires -all -parallel -openmp 8 




recon-all -subjid sub-03psbcstript1map  \
    -i $proj_path/derivatives/MP2RAGE_preprocess/sub-03b/presurf_final_outputs/UNI_masked.nii \
    -T2 $proj_path/derivatives/MP2RAGE_preprocess/sub-03b/presurf_final_outputs/T1map_masked.nii.gz -T2pial \
    -hires -all -parallel -openmp 8 


recon-all -subjid sub-## -i MPRAGEised_biascorrected_masked_uni.nii -T2 t1map_masked.nii -T2pial -hires -all 
```






# NEW ATTEMPT
- Presurfer: 
- inv2
- MPRAGEiSE -> SANLM -> mask with edited stripmask
-> & push through presurf_UNI
-> take brainmask of this and apply to T1
-> use this as the T2 
```bash

proj_path="/Users/marcusdaghlian/projects/pilot-clean-link"
export SUBJECTS_DIR=$proj_path/derivatives/freesurfer

TPATH="${proj_path}/derivatives/MP2RAGE_preprocess/sub-03b/for_fs"

recon-all -subjid sub-03stripT2bmask -i  "${TPATH}/sub-03_masked_uni.nii.gz" -T2 "${TPATH}/sub-03_T1map_skull_stripped.nii.gz" -T2pial -hires -all 


recon-all -subjid sub-03bmaskT2bmask -i  "${TPATH}/sub-03_brainmasked_uni.nii.gz" -T2 "${TPATH}/sub-03_T1map_skull_stripped.nii.gz" -T2pial -hires -all 
```
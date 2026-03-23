# Get environment ready
```bash
conda activate mp2rage_preproc01
BIDS_DIR=/Users/marcusdaghlian/projects/dp-clean-link/pilot-clean/
DERIV_DIR=$BIDS_DIR/derivatives/
export SUBEJCTS_DIR=$DERIV_DIR/freesurfer
SUB=sub-ht2
SES=ses-1
MP2RAGE_OUT=$DERIV_DIR/MP2RAGE_preprocess/${SUB}
uni=$(find $BIDS_DIR/$SUB/$SES/anat -name "*uni*")
inv1=$(find $BIDS_DIR/$SUB/$SES/anat -name "*inv1*")
inv2=$(find $BIDS_DIR/$SUB/$SES/anat -name "*inv2*")
T1map=$(find $BIDS_DIR/$SUB/$SES/anat -name "*t1*")
mp2rage_script_dir=/Users/marcusdaghlian/projects/dp-clean-link/pilot-clean/code/stripes_pipline/preprocessing/anatomy/MP2RAGE_preproc
```

# [A] Anatomical preprocessing 
Preprocess mp2rage - denoise; get brain mask etc. 

```bash
python s01_mp2rage_preproc.py \
    --subject $SUB \
    --session $SES \
    --outdir $MP2RAGE_OUT \
    --uni $uni --inv2 $inv2 --mp2rage-script-dir $mp2rage_script_dir 
```

## [B] Run freesurfer - split into steps 
- Does autorecon1 - without skull strip
- Then injects the skull strip (which we did before with SPM)
- Then does a QC check
- Finally run autorecon2 & 3, all steps as in 

```bash
uni_mpragised=$(find $MP2RAGE_OUT/ -name "*UNI-mpragised.nii.gz")
brain_mask=$(find $MP2RAGE_OUT/ -name "*_brainmask.nii")

python s02_mp2rage_fs.py \
    --subject $SUB \
    --subjects-dir $SUBJECTS_DIR \
    --uni-mpragised $uni_mpragised --brain-mask $brain_mask \
    --extra-flags -hires 
```
## extra steps - run benson atlas & get flatmaps with pycortex
```bash
conda activate b14
python s02_b14atlas.py $SUB --fsdir $SUBJECTS_DIR

# -> autoflatten
conda activate autoflat
autoflatten $SUBJECTS_DIR/$SUB

# -> pycortex import 
conda activate pctx01 
python s04_pycortex.py $SUB --fsdir $SUBJECTS_DIR
```

# ********
# Functional 
- Nothing fancy - simply run spm_realign to get all runs in one space
- glm_single + alignment in notebook (will pull out at a later stage)
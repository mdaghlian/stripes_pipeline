# overview - MP2RAGE

INV1 - (Short inversion time)
* Very strong T1 weighting 
* *Can also get phase & magnitude*

INV2 - (Longer inversion time)
- Contrast is **closer to proton-density–like** (still T1-influenced, just flatter)
- **Higher SNR** than INV1
- Less sharp tissue contrast than INV1
- Captures much of the **receive and transmit field bias (B1⁻ / B1⁺)**
- Can reconstruct **magnitude and phase**
* *Can also get phase & magnitude*

UNI (uniform T1-weighted image)
* Synthetic image created by combining INV1 & INV2
* High contrast, noise is suppressed by using ratio of INV1 and INV2
* This is what you want to use generally in segmentation 
T1 map (quantitative T1)
- Produces **voxel-wise quantitative T1 values (in ms)**
- Closer to **physical tissue properties** than weighted images
- Requires **specific acquisition parameters** (TI1, TI2, flip angles, TR, etc.)
- More robust to scanner-dependent intensity scaling

Note - for UNI, and T1map, scanners vendors will often do calculations for you, with proprietary techniques. but it can be improved sometimes. 

There can be 2 flavours of thing that comes off the scanner:
**(a) two magnitude images (one for each inversion) and a unified T1w image**  
Although the approach described by O'Brien et al. based on raw data, [JosePMarques](https://github.com/JosePMarques)'s implementation can be used to create a denoised unified T1w image from two magnitude and a unified T1w image.  
**(b) a phase and a magnitude image for each the first and second inversion**  
These images can then be used to create a unified T1w image or a denoised unified T1w image using the methods proposed by Marques et al. and O'Brien et al. respectively.



There are a couple of problems, that give freesurfer headaches
[1] Speckle noise 
[2] (although not unique to MP2RAGE) - saggital sinus, pial stuff etc. 

Anything that can be done to reduce the manual labour in freesurfer is good!

# Strategies for denoising MP2RAGE: 

## Robust re-calculation of UNI image
- see Jose Marques & O'Brien
- Also LAYNII implementation

## Bias correct & use INV2-mag to threshold
Presurfer - & also 
e.g., from TKNapen (circa 2018) 
Do bias correction on INV2 image; 
```python 
nilearn.masking.compute_background_mask
```

# Jurjen pipeline (fmriproc)
- again focus is to make as clean & nice freesurfer segmentation as possible
- however, a simplified version may be possible (not all steps below are necessary)

04: spinoza_qmrimaps: wrapper for pymp2rage
* wrapper for estimation of T1 and other parametric maps from the (ME)MP2RAGE sequences by throwing
* the two inversion and phase images in PYMP2RAGE (https://github.com/Gilles86/pymp2rage).
* requires the phase

07: spinoza_sinusfrommni:
* dilated sinus mask from registering with MNI, used later to improve the sinus mask from T1 T2 ratio

08: spinoza_biassanlm
* Sometimes CAT12 can be a bit of an overkill with smoothing and bias corrections. This script should
* be run prior to "spinoza_brainextraction", and runs a SANLM-filter over the image as well as an biasfield correction with SPM. The subsequent "spinoza_brainextraction" should be run with the "-m brain"
* flag as to turn off bias correction and denoising with CAT12. The input image is expected to reside
* in the input directory and to contain "acq-${DATA}" and end with *T1w.nii.gz.*

09:spinoza_brainextraction
* wrapper for brain extraction with ANTs, FSL, or CAT12 If you use ANTs, specify a prefix; if you use
* FSL, specify an output name. Not case sensitive (i.e., you can use ANTs/ants or FSL/fsl). Assumes
* that if you select FSL, we brain extract the INV2 image and ***if we select ANTs/CAT12, we brain extract the mp2rage T1w with bias field correction***. If you want to brain extract something else, either use
* call_fslbet, call_antsbet, or call_cat12. It performs N4 biasfield correction internally. Make sure
* you added the location of antsBrainExtraction.sh to your path e.g., in your ~/.bash_profile :

11 spinoza_dura
* estimate the location of the skull and dura using nighres. You are to specify the path to the input T1w-images (e.g., pymp2rage), the input INV2 image (e.g., the bias field corrected INV2 in the ANTsfolder, the nighres output folder, and the folder to store the masks.

12 spinoza_sagittalsinus
* This script creates the sagittal sinus mask based on the R2*-map from pymp2rage. It requires the user to refine the mask a bit, because the R2*-map is imperfect especially around the putamen and other iron-rich regions inside the brain. It will start ITKsnap for the user to do the editing.

13: spinoza_masking
* Mask out the dura and skull from the T1-image to reduce noise. It follow Gilles' masking procedure, by setting the contents of dura ('outside') and other masks ('inside') to zero. The idea is to run this, run fMRIprep, check segmentations, manually edit it as "${SUBJECT_PREFIX}xxx_ses-1_acq-MP2RAGE_desc-manualwmseg" or something alike. These 'manualseg' will be taken as 'inside' to boost areas that were not counted as brain.



I'm coming up with the best strategy to prep the MP2RAGE for freesurfer - based on your pipeline


# [O'Brien, et al, 2014.](doi:10.1371/journal.pone.0099676) robust T1-weighted

# [Marques & Gruetter 2013](https://doi.org/10.1371/journal.pone.0069294)

See also [Jose Marques github](https://github.com/JosePMarques/MP2RAGE-related-scripts/tree/master)

Uni is created by combination of INV1 & INV2
Both INV1 & INV2 are taken as complex images. $\star$ stands for complex conjugate

$$Uni = \frac{\tt{INV1} \times \tt{INV2\star}}{\tt{INV1}^2 \times \tt{INV2}^2}
$$

Can be combined with Sa2RAGE... something something - it helps


# [pymp2rage](https://github.com/Gilles86/pymp2rage)
This package is a lightweight python implementation of the algorithms described in Marques et al. (2010). They can be used to compute a unified T1-weighted, as well as a quantiative T1 map out of the two phase- and magnitude-images of a MP2RAGE-sequences.





# Links: 
* https://github.com/srikash/presurfer
* https://github.com/gjheij/fmriproc
* https://fmriproc.readthedocs.io/en/latest/
* https://github.com/gjheij/linescanning
* https://linescanning.readthedocs.io/en/latest/
* https://layerfmri.com/2019/06/22/mp2rage/
* https://neurostars.org/t/mp2rage-in-bids-and-fmriprep/2008/16?page=2
* https://github.com/nipreps/smriprep/issues/18
* 



# python
```python
#!/usr/bin/env python
from __future__ import print_function

import sys
import numpy as np

import nibabel as nib

############################################
# Note: Python implemention of matlab code https://github.com/khanlab/mp2rage_genUniDen.git mp2rage_genUniDen.m
# Date: 2019/09/25
# Author: YingLi Lu
# Fully tested on python3(can run on python2.7 as well), get exactly same result image with matlab.
############################################

# ignore RuntimeWarning: invalid value encountered in true_divide
np.seterr(all='ignore')


def MP2RAGErobustfunc(INV1, INV2, beta):
    # matalb: MP2RAGErobustfunc=@(INV1,INV2,beta)(conj(INV1).*INV2-beta)./(INV1.^2+INV2.^2+2*beta);
    return (np.conj(INV1)*INV2-beta)/(INV1**2+INV2**2+2*beta)


def rootsquares_pos(a, b, c):
    # matlab:rootsquares_pos=@(a, b, c)(-b+sqrt(b. ^ 2 - 4 * a.*c))./(2*a)
    return (-b+np.sqrt(b**2 - 4*a*c))/(2*a)


def rootsquares_neg(a, b, c):
    # matlab: rootsquares_neg = @(a, b, c)(-b-sqrt(b. ^ 2 - 4 * a.*c))./(2*a)
    return (-b-np.sqrt(b**2 - 4*a*c))/(2*a)


def mp2rage_genUniDen(MP2RAGE_filenameUNI, MP2RAGE_filenameINV1, MP2RAGE_filenameINV2, MP2RAGE_uniden_output_filename, chosenFactor):
    #########
    # load data
    #########
    MP2RAGEimg = nib.load(MP2RAGE_filenameUNI)
    INV1img = nib.load(MP2RAGE_filenameINV1)
    INV2img = nib.load(MP2RAGE_filenameINV2)

    MP2RAGEimg_img = MP2RAGEimg.get_fdata()
    INV1img_img = INV1img.get_fdata()
    INV2img_img = INV2img.get_fdata()

    if MP2RAGEimg_img.min() >= 0 and MP2RAGEimg_img.max() >= 0.51:
       # converts MP2RAGE to -0.5 to 0.5 scale - assumes that it is getting only positive values
        MP2RAGEimg_img = (
            MP2RAGEimg_img - MP2RAGEimg_img.max()/2)/MP2RAGEimg_img.max()
        integerformat = 1
    else:
        integerformat = 0

    #########
    # computes correct INV1 dataset
    #########
    # gives the correct polarity to INV1
    INV1img_img = np.sign(MP2RAGEimg_img)*INV1img_img

    # because the MP2RAGE INV1 and INV2 is a sum of squares data, while the
    # MP2RAGEimg is a phase sensitive coil combination.. some more maths has to
    # be performed to get a better INV1 estimate which here is done by assuming
    # both INV2 is closer to a real phase sensitive combination

    # INV1pos=rootsquares_pos(-MP2RAGEimg.img,INV2img.img,-INV2img.img.^2.*MP2RAGEimg.img);
    INV1pos = rootsquares_pos(-MP2RAGEimg_img,
                              INV2img_img, -INV2img_img**2*MP2RAGEimg_img)
    INV1neg = rootsquares_neg(-MP2RAGEimg_img,
                              INV2img_img, -INV2img_img**2*MP2RAGEimg_img)

    INV1final = INV1img_img

    INV1final[np.absolute(INV1img_img-INV1pos) > np.absolute(INV1img_img-INV1neg)
              ] = INV1neg[np.absolute(INV1img_img-INV1pos) > np.absolute(INV1img_img-INV1neg)]
    INV1final[np.absolute(INV1img_img-INV1pos) <= np.absolute(INV1img_img-INV1neg)
              ] = INV1pos[np.absolute(INV1img_img-INV1pos) <= np.absolute(INV1img_img-INV1neg)]

    # usually the multiplicative factor shouldn't be greater then 10, but that
    # is not the ase when the image is bias field corrected, in which case the
    # noise estimated at the edge of the imagemight not be such a good measure

    multiplyingFactor = chosenFactor
    noiselevel = multiplyingFactor*np.mean(INV2img_img[:, -11:, -11:])

    # % MP2RAGEimgRobustScanner = MP2RAGErobustfunc(INV1img.img, INV2img.img, noiselevel. ^ 2)
    MP2RAGEimgRobustPhaseSensitive = MP2RAGErobustfunc(
        INV1final, INV2img_img, noiselevel**2)

    if integerformat == 0:
        MP2RAGEimg_img = MP2RAGEimgRobustPhaseSensitive
    else:
        MP2RAGEimg_img = np.round(4095*(MP2RAGEimgRobustPhaseSensitive+0.5))

    #########
    # save image
    #########
    MP2RAGEimg_img = nib.casting.float_to_int(MP2RAGEimg_img,'int16');
    new_MP2RAGEimg = nib.Nifti1Image(MP2RAGEimg_img, MP2RAGEimg.affine, MP2RAGEimg.header)
    nib.save(new_MP2RAGEimg, MP2RAGE_uniden_output_filename)
```
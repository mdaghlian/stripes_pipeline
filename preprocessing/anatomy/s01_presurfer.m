%% MP2RAGE Pre-processing Pipeline - Optimized for FreeSurfer
% Complete pipeline with background noise removal
% Based on presurfer workflow and RobustCombination method
%
% Pipeline order:
% 1. Process INV2 -> bias correct -> create brain mask
% 2. MPRAGEise: multiply denoised UNI with normalized bias-corrected INV2
% 3. Bias correct the MPRAGEised image
% 4. SANLM denoise the bias-corrected MPRAGEised image

%% Configuration
MP2SOURCE_PATH = '/Users/marcusdaghlian/projects/pilot-clean-link/derivatives/MP2RAGE_preprocess/sub-03b';
UNI = fullfile(MP2SOURCE_PATH, 'sub-03_acq-MP2RAGE_UNI.nii');
INV1 = fullfile(MP2SOURCE_PATH, 'sub-03_acq-MP2RAGE_inv-1.nii');
INV2 = fullfile(MP2SOURCE_PATH, 'sub-03_acq-MP2RAGE_inv-2.nii');
T1map = fullfile(MP2SOURCE_PATH, 'sub-03_acq-MP2RAGE_T1map.nii');

%% Run Optimized Pipeline
% Step 1: process the INV2 image (bias correct, & create strip mask)
[INV2bc, strip_mask]=presurf_INV2(INV2);

% Step 2: MPRAGEise using denoised UNI
UNI_out = presurf_MPRAGEise(INV2bc, UNI);

% Step 3: Bias correction
UNI_out = presurf_biascorrect(UNI_out);


% Clean up files for final denoised path
mkdir(MP2SOURCE_PATH,'presurf_final_outputs')
% copy strip mask, uni out
% Copy the strip mask and UNI_out to the final outputs directory
copyfile(strip_mask, fullfile(MP2SOURCE_PATH, 'presurf_final_outputs', 'strip_mask.nii'));
copyfile(UNI_out, fullfile(MP2SOURCE_PATH, 'presurf_final_outputs', 'UNI_out.nii'));

disp('PresurferB pipeline complete. Final outputs saved in presurf_final_outputs folder.');
disp('Now check the mask & uni visually with ITK snap, and make necessary edits')
disp('Then mask the UNI_out, and pass to freesurfer recon-all with -hires flag');


% Step 4: SANLM denoising - not needed 
% UNI_out = presurf_SANLM(UNI_out);

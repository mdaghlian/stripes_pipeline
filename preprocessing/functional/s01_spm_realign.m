% s00_preproc_paths;
func_paths = '/Users/marcusdaghlian/projects/pilot-clean-link/derivatives/spm_align/sub-ht2/';
% Check if directory exists
if ~exist(func_paths, 'dir')
    error('Directory does not exist!');
end
% Get all your fMRI files
files = {
    spm_select('ExtFPList', fullfile(func_paths), '.*\.nii$', Inf)
};

% Realign - estimates movement parameters
spm_realign(files);

% Reslice - applies transformation in ONE interpolation step
% Use mean image as reference
flags.mean = 1;
flags.which = 2; % reslice all images
flags.interp = 4; % 4th degree B-spline (good quality)
% flags.estimate
spm_reslice(files, flags);

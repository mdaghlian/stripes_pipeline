function [INV2bc, strip_mask]=presurf_INV2(full_path_to_file)
disp(' ');
disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
disp([datestr(datetime('now')), '        Start Pre-processing INV2']);
disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
disp(' ');

%% Check SPM
spm_directory = presurf_helper.check_spm_path();

%% Handle input
if nargin < 1 || isempty(full_path_to_file)
    [in_file_name, in_file_path] = uigetfile('*.nii;*.nii.gz', 'Select Input File');
    full_path_to_file = fullfile(in_file_path, in_file_name);
end
disp(['> Input: ', full_path_to_file]);

%% Setup output directory
[in_file_path, in_file_prefix, in_file_ext] = fileparts(full_path_to_file);
full_path_to_out = fullfile(in_file_path, 'presurf_INV2');

if ~exist(full_path_to_out, 'dir')
    mkdir(full_path_to_out);
    disp(['> Created output directory: ', full_path_to_out]);
end

%% Unzip if needed
full_path_to_file = presurf_helper.unzip_if_needed(full_path_to_file, in_file_path, in_file_prefix, in_file_ext);
[~, in_file_prefix, ~] = fileparts(full_path_to_file);
in_file_name = [in_file_prefix, '.nii'];


%% Make copy
copyfile(full_path_to_file, ...
    fullfile(full_path_to_out, in_file_name));

%% Setup SPM Batch
clear matlabbatch;
matlabbatch{1}.spm.spatial.preproc.channel.vols = {[fullfile(full_path_to_out,in_file_name),',1']};
matlabbatch{1}.spm.spatial.preproc.channel.biasreg = 0.001;
matlabbatch{1}.spm.spatial.preproc.channel.biasfwhm = 30;
matlabbatch{1}.spm.spatial.preproc.channel.write = [1 1];
matlabbatch{1}.spm.spatial.preproc.tissue(1).tpm = {[fullfile(spm_directory, 'tpm','TPM.nii'),',1']};
matlabbatch{1}.spm.spatial.preproc.tissue(1).ngaus = 2;
matlabbatch{1}.spm.spatial.preproc.tissue(1).native = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(1).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(2).tpm = {[fullfile(spm_directory, 'tpm','TPM.nii'),',2']};
matlabbatch{1}.spm.spatial.preproc.tissue(2).ngaus = 2;
matlabbatch{1}.spm.spatial.preproc.tissue(2).native = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(2).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(3).tpm = {[fullfile(spm_directory, 'tpm','TPM.nii'),',3']};
matlabbatch{1}.spm.spatial.preproc.tissue(3).ngaus = 2;
matlabbatch{1}.spm.spatial.preproc.tissue(3).native = [1 0];
matlabbatch{1}.spm.spatial.preproc.tissue(3).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(4).tpm = {[fullfile(spm_directory, 'tpm','TPM.nii'),',4']};
matlabbatch{1}.spm.spatial.preproc.tissue(4).ngaus = 3;
matlabbatch{1}.spm.spatial.preproc.tissue(4).native = [1 0];
matlabbatch{1}.spm.spatial.preproc.tissue(4).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(5).tpm = {[fullfile(spm_directory, 'tpm','TPM.nii'),',5']};
matlabbatch{1}.spm.spatial.preproc.tissue(5).ngaus = 4;
matlabbatch{1}.spm.spatial.preproc.tissue(5).native = [1 0];
matlabbatch{1}.spm.spatial.preproc.tissue(5).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(6).tpm = {[fullfile(spm_directory, 'tpm','TPM.nii'),',6']};
matlabbatch{1}.spm.spatial.preproc.tissue(6).ngaus = 2;
matlabbatch{1}.spm.spatial.preproc.tissue(6).native = [1 0];
matlabbatch{1}.spm.spatial.preproc.tissue(6).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.warp.mrf = 1;
matlabbatch{1}.spm.spatial.preproc.warp.cleanup = 1;
matlabbatch{1}.spm.spatial.preproc.warp.reg = [0 0.001 0.5 0.05 0.2];
matlabbatch{1}.spm.spatial.preproc.warp.affreg = 'mni'; %'eastern'
matlabbatch{1}.spm.spatial.preproc.warp.fwhm = 0;
matlabbatch{1}.spm.spatial.preproc.warp.samp = 2;
matlabbatch{1}.spm.spatial.preproc.warp.write = [0 0];
matlabbatch{1}.spm.spatial.preproc.warp.vox = NaN;
matlabbatch{1}.spm.spatial.preproc.warp.bb = [NaN NaN NaN
    NaN NaN NaN];
%% Start SPM Job
disp(' ');
disp('++++ Starting Segmentation');
spm('defaults', 'FMRI');
spm_jobman('run', matlabbatch);

%% Clean up output files
INV2bc = fullfile(full_path_to_out, [in_file_prefix, '_biascorrected.nii']);
strip_mask = fullfile(full_path_to_out, [in_file_prefix, '_stripmask.nii']);
% Remove mat file
delete(fullfile(full_path_to_out,[in_file_prefix,'_seg8.mat']));
save(fullfile(full_path_to_out,[in_file_prefix,'_presurfSegBatch.mat']),'matlabbatch');

% Bias corrected file
copyfile(fullfile(full_path_to_out,['m',in_file_name]), fullfile(full_path_to_out,[in_file_prefix,'_biascorrected.nii']));
delete(fullfile(full_path_to_out,['m',in_file_name]));

% Bias field file
copyfile(fullfile(full_path_to_out,['BiasField_',in_file_name]), fullfile(full_path_to_out,[in_file_prefix,'_biasfield.nii']));
delete(fullfile(full_path_to_out,['BiasField_',in_file_name]));

% Rename C3
copyfile(fullfile(full_path_to_out,['c3',in_file_name]), fullfile(full_path_to_out,[in_file_prefix,'_class3.nii']));
delete(fullfile(full_path_to_out,['c3',in_file_name]));
% Rename C4
copyfile(fullfile(full_path_to_out,['c4',in_file_name]), fullfile(full_path_to_out,[in_file_prefix,'_class4.nii']));
delete(fullfile(full_path_to_out,['c4',in_file_name]));
% Rename C5
copyfile(fullfile(full_path_to_out,['c5',in_file_name]), fullfile(full_path_to_out,[in_file_prefix,'_class5.nii']));
delete(fullfile(full_path_to_out,['c5',in_file_name]));
% Rename C6
copyfile(fullfile(full_path_to_out,['c6',in_file_name]), fullfile(full_path_to_out,[in_file_prefix,'_class6.nii']));
delete(fullfile(full_path_to_out,['c6',in_file_name]));

%% Combine masks
clear matlabbatch;
matlabbatch{1}.spm.util.imcalc.input = {
    fullfile(full_path_to_out,[in_file_prefix,'_class3.nii'])
    fullfile(full_path_to_out,[in_file_prefix,'_class4.nii'])
    fullfile(full_path_to_out,[in_file_prefix,'_class5.nii'])
    fullfile(full_path_to_out,[in_file_prefix,'_class6.nii'])
    };
matlabbatch{1}.spm.util.imcalc.output = fullfile(full_path_to_out,[in_file_prefix,'_stripmask.nii']);
matlabbatch{1}.spm.util.imcalc.outdir = {''};
matlabbatch{1}.spm.util.imcalc.expression = '1-((i1+i2+i3+i4)>0.5)';
matlabbatch{1}.spm.util.imcalc.var = struct('name', {}, 'value', {});
matlabbatch{1}.spm.util.imcalc.options.dmtx = 0;
matlabbatch{1}.spm.util.imcalc.options.mask = 0;
matlabbatch{1}.spm.util.imcalc.options.interp = -7;
matlabbatch{1}.spm.util.imcalc.options.dtype = 2;
%% Start SPM Job
disp(' ');
disp('++++ Preparing Stripmask');
spm('defaults', 'FMRI');
spm_jobman('run', matlabbatch);
save(fullfile(full_path_to_out,[in_file_prefix,'_presurfStripBatch.mat']),'matlabbatch');
%% Fin
disp(' ');
disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
disp([datestr(datetime('now')), '        Completed Pre-processing INV2']);
disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
disp(' ');
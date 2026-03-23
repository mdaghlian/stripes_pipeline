function full_path_to_output = presurf_biascorrect(full_path_to_file)
    %% ========================================================================
    %  FUNCTION: presurf_biascorrect
    %  ========================================================================

    disp(' ');
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp([datestr(datetime('now')), '        Starting SPM Bias-correction']);
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
    full_path_to_out = fullfile(in_file_path, 'presurf_biascorrect');
    
    if ~exist(full_path_to_out, 'dir')
        mkdir(full_path_to_out);
        disp(['> Created output directory: ', full_path_to_out]);
    end
    
    %% Unzip if needed
    full_path_to_file = presurf_helper.unzip_if_needed(full_path_to_file, in_file_path, in_file_prefix, in_file_ext);
    [~, in_file_prefix, ~] = fileparts(full_path_to_file);
    in_file_name = [in_file_prefix, '.nii'];
    
    %% Copy to output directory
    copyfile(full_path_to_file, fullfile(full_path_to_out, in_file_name));
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
    matlabbatch{1}.spm.spatial.preproc.tissue(3).native = [0 0];
    matlabbatch{1}.spm.spatial.preproc.tissue(3).warped = [0 0];
    matlabbatch{1}.spm.spatial.preproc.tissue(4).tpm = {[fullfile(spm_directory, 'tpm','TPM.nii'),',4']};
    matlabbatch{1}.spm.spatial.preproc.tissue(4).ngaus = 3;
    matlabbatch{1}.spm.spatial.preproc.tissue(4).native = [0 0];
    matlabbatch{1}.spm.spatial.preproc.tissue(4).warped = [0 0];
    matlabbatch{1}.spm.spatial.preproc.tissue(5).tpm = {[fullfile(spm_directory, 'tpm','TPM.nii'),',5']};
    matlabbatch{1}.spm.spatial.preproc.tissue(5).ngaus = 4;
    matlabbatch{1}.spm.spatial.preproc.tissue(5).native = [0 0];
    matlabbatch{1}.spm.spatial.preproc.tissue(5).warped = [0 0];
    matlabbatch{1}.spm.spatial.preproc.tissue(6).tpm = {[fullfile(spm_directory, 'tpm','TPM.nii'),',6']};
    matlabbatch{1}.spm.spatial.preproc.tissue(6).ngaus = 2;
    matlabbatch{1}.spm.spatial.preproc.tissue(6).native = [0 0];
    matlabbatch{1}.spm.spatial.preproc.tissue(6).warped = [0 0];
    matlabbatch{1}.spm.spatial.preproc.warp.mrf = 1;
    matlabbatch{1}.spm.spatial.preproc.warp.cleanup = 1;
    matlabbatch{1}.spm.spatial.preproc.warp.reg = [0 0.001 0.5 0.05 0.2];
    matlabbatch{1}.spm.spatial.preproc.warp.affreg = 'mni'; %'eastern'
    matlabbatch{1}.spm.spatial.preproc.warp.fwhm = 0;
    matlabbatch{1}.spm.spatial.preproc.warp.samp = 3;
    matlabbatch{1}.spm.spatial.preproc.warp.write = [0 0];
    matlabbatch{1}.spm.spatial.preproc.warp.vox = NaN;
    matlabbatch{1}.spm.spatial.preproc.warp.bb = [NaN NaN NaN
                                                NaN NaN NaN];
    %% Run SPM job
    disp('++++ Running bias correction...');
    spm('defaults', 'FMRI');
    spm_jobman('run', matlabbatch);
    save(fullfile(full_path_to_out, [in_file_prefix, '_presurfBiasCorrBatch.mat']), 'matlabbatch');
    
    %% Rename outputs
    delete(fullfile(full_path_to_out, [in_file_prefix, '_seg8.mat']));
    
    movefile(fullfile(full_path_to_out, ['m', in_file_name]), ...
             fullfile(full_path_to_out, [in_file_prefix, '_biascorrected.nii']));
    
    movefile(fullfile(full_path_to_out, ['BiasField_', in_file_name]), ...
             fullfile(full_path_to_out, [in_file_prefix, '_biasfield.nii']));
    
    full_path_to_output = fullfile(full_path_to_out, [in_file_prefix, '_biascorrected.nii']);
    
    disp(' ');
    disp(['> Output: ', full_path_to_output]);
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp([datestr(datetime('now')), '        Completed SPM Bias-correction']);
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp(' ');
end
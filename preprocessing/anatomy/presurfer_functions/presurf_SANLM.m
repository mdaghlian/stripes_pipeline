function full_path_to_output = presurf_SANLM(full_path_to_file)
    %% ========================================================================
    %  FUNCTION: presurf_SANLM
    %  ========================================================================

    disp(' ');
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp([datestr(datetime('now')), '        Starting SANLM Denoising']);
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
    full_path_to_out = fullfile(in_file_path, 'presurf_SANLM');
    
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
    
    %% Setup SPM batch
    clear matlabbatch;
    matlabbatch{1}.spm.tools.cat.tools.sanlm.data = {[fullfile(full_path_to_out, in_file_name), ',1']};
    matlabbatch{1}.spm.tools.cat.tools.sanlm.prefix = 'sanlm_';
    matlabbatch{1}.spm.tools.cat.tools.sanlm.NCstr = Inf;
    matlabbatch{1}.spm.tools.cat.tools.sanlm.rician = 0;
    
    %% Run SPM job
    disp('++++ Running SANLM denoising...');
    spm('defaults', 'FMRI');
    spm_jobman('run', matlabbatch);
    
    full_path_to_output = fullfile(full_path_to_out, ['sanlm_', in_file_name]);
    
    disp(' ');
    disp(['> Output: ', full_path_to_output]);
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp([datestr(datetime('now')), '        Completed SANLM Denoising']);
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp(' ');
end

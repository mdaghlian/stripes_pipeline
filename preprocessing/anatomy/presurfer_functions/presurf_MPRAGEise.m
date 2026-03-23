function full_path_to_output = presurf_MPRAGEise(full_path_to_inv2bc, full_path_to_uni)
    %% ========================================================================
    %  FUNCTION: presurf_MPRAGEise
    %  ========================================================================

    disp(' ');
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp([datestr(datetime('now')), '        Start MPRAGEising']);
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp(' ');
    
    %% Check SPM
    spm_directory = presurf_helper.check_spm_path();
    
    %% Handle inputs
    if nargin < 1 || isempty(full_path_to_inv2bc)
        [inv2_file_name, inv2_file_path] = uigetfile('*.nii;*.nii.gz', 'Select INV2');
        full_path_to_inv2bc = fullfile(inv2_file_path, inv2_file_name);
    end
    disp(['> INV2: ', full_path_to_inv2bc]);
    
    if nargin < 2 || isempty(full_path_to_uni)
        [uni_file_name, uni_file_path] = uigetfile('*.nii;*.nii.gz', 'Select UNI image');
        full_path_to_uni = fullfile(uni_file_path, uni_file_name);
    end
    disp(['> UNI: ', full_path_to_uni]);
    
    %% Unzip if needed
    [inv2_file_path, inv2_file_prefix, inv2_ext] = fileparts(full_path_to_inv2bc);
    full_path_to_inv2bc = presurf_helper.unzip_if_needed(full_path_to_inv2bc, inv2_file_path, inv2_file_prefix, inv2_ext);
    [~, inv2_file_prefix, ~] = fileparts(full_path_to_inv2bc);
    
    [uni_file_path, uni_file_prefix, uni_ext] = fileparts(full_path_to_uni);
    full_path_to_uni = presurf_helper.unzip_if_needed(full_path_to_uni, uni_file_path, uni_file_prefix, uni_ext);
    [~, uni_file_prefix, ~] = fileparts(full_path_to_uni);
    
    
    %% MPRAGEise: multiply UNI by normalized INV2
    disp(' ');
    disp('++++ Creating MPRAGEised image...');
    
    uni_nii = spm_vol(full_path_to_uni);
    uni_img = spm_read_vols(uni_nii);
    
    inv2_img = spm_read_vols(spm_vol(full_path_to_inv2bc));
    inv2_img_norm = mat2gray(inv2_img);
    
    uni_img_mpraged = uni_img .* inv2_img_norm;
    
    % Save output
    uni_nii.fname = fullfile(uni_file_path, [uni_file_prefix, '_MPRAGEised.nii']);
    spm_write_vol(uni_nii, uni_img_mpraged);
    
    full_path_to_output = uni_nii.fname;
    
    disp(' ');
    disp(['> Output: ', full_path_to_output]);
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp([datestr(datetime('now')), '        Completed MPRAGEising']);
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp(' ');
end

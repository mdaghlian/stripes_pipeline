classdef presurf_helper
    methods (Static)
    % --------------------------------------------------------
    % --------------------------------------------------------
    function spm_directory = check_spm_path()
        % Check if SPM is in path and add if needed
        if exist('spm', 'file') == 0
            disp('++++ SPM directory not found in path.');
            spm_directory = uigetdir(pwd, 'Select directory with SPM 12');
            addpath(spm_directory);
            disp(['> Added to path: ', spm_directory]);
        else
            spm_directory = which('spm');
            spm_directory = spm_directory(1:end-6);
            disp(['> SPM found: ', spm_directory]);
        end
    end
    % --------------------------------------------------------
    % --------------------------------------------------------
    function full_path_out = unzip_if_needed(full_path_in, file_path, file_prefix, file_ext)
        % Unzip .nii.gz files if needed
        if strcmp(file_ext, '.gz')
            disp(['> Unzipping: ', full_path_in]);
            gunzip(full_path_in);
            delete(full_path_in);
            full_path_out = fullfile(file_path, file_prefix);
            disp(['> Unzipped: ', full_path_out]);
        else
            disp(['> File already unzipped: ', full_path_in]);
            full_path_out = full_path_in;
        end
    end
    % --------------------------------------------------------
    % --------------------------------------------------------
    end
end
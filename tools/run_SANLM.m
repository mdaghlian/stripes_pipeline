function presurf_SANLM(full_path_to_file)
disp(' ');
disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
disp([datestr(datetime('now')),'        Start Pre-processing UNI - sanlm']);
disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
disp(' ');
%% Check if SPM Directory exists on path
if exist('spm') == 0
    disp('++++ SPM directory not found in path.');
    disp(' ');
    spm_directory = uigetdir(pwd, 'Select directory with SPM 12');
    addpath(spm_directory);
    disp(['> ', spm_directory]);
    disp('> Added to path');
else
    spm_directory = which('spm');
    spm_directory = spm_directory(1:end - 6);
    disp('++++ SPM directory exists in path.');
    disp(['> ', spm_directory]);
end
%% Select Data
if exist('full_path_to_file', 'var') == 1
    disp(' ');
    disp('++++ Input File Provided.');
    disp(['> ', full_path_to_file]);
else
    [in_file_name,in_file_path] = uigetfile('*.nii;*.nii.gz', 'Select Input File');
    disp(' ');
    disp('++++ Input File Selected.');
    full_path_to_file=fullfile(in_file_path,in_file_name);
    disp(['> ', full_path_to_file]);
end

% make outpath directory
[in_file_path, in_file_prefix, in_file_ext] = fileparts(full_path_to_file);
full_path_to_out = fullfile(in_file_path, 'presurf_SANLM');
mkdir(full_path_to_out);
disp(' ');
disp('++++ Output Directory Created.');
disp(['> ', full_path_to_out]);

if in_file_ext == ".gz"
    disp(' ');
    disp('++++ Unzipping Input file');
    disp(['> ', full_path_to_file]);
    gunzip(full_path_to_file);
    delete(full_path_to_file);
    in_file_name=in_file_prefix;
    disp('++++ Unzipped Input file');
    full_path_to_file=fullfile(in_file_path,in_file_name);
    [~, in_file_prefix, ~] = fileparts(full_path_to_file);
    disp(['> ', full_path_to_file]);
else
    disp('++++ Input file is unzipped');
    in_file_name=[in_file_prefix,'.nii'];
    disp(['> ', full_path_to_file]);
end

%% Make copy
copyfile(full_path_to_file, ...
    fullfile(full_path_to_out, in_file_name));

%% Setup SPM Batch
clear matlabbatch;
matlabbatch{1}.spm.tools.cat.tools.sanlm.data = {[fullfile(full_path_to_out,in_file_name),',1']};
matlabbatch{1}.spm.tools.cat.tools.sanlm.prefix = 'sanlm_';
matlabbatch{1}.spm.tools.cat.tools.sanlm.NCstr = Inf;
matlabbatch{1}.spm.tools.cat.tools.sanlm.rician = 0;

%% Start SPM Job
disp(' ');
spm('defaults', 'FMRI');
spm_jobman('run', matlabbatch);
%save(fullfile(full_path_to_out,[in_file_prefix,'_presurfWMBatch.mat']),'matlabbatch');

%% Fin
disp(' ');
disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
disp([datestr(datetime('now')),'        Completed SANLM']);
disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
disp(' ');

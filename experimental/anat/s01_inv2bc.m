function s01_inv2bc(sub)
% Bias correct the inv2 image
sub = char(sub);

% Load paths (must set mp2source_path and inv2bc_path)
s00_preproc_paths;

% Build subject directories
sub_mp2path    = fullfile(mp2source_path, sub);

% Ensure source folder exists
if ~isfolder(sub_mp2path)
    error('s01_inv2bc:NoSourceFolder', 'Source folder does not exist: %s', sub_mp2path);
end

% Find files matching pattern
inv2_file = dir(fullfile(sub_mp2path, '*inv2*'));

% Step - 1: bias correct inv2
presurf_biascorrect(fullfile(inv2_file.folder, inv2_file.name));
end
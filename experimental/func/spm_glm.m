% SPM GLM Analysis Script
% This script performs a first-level GLM analysis with 2 tasks across 3 runs

clear all;
close all;

% Initialize SPM
spm('defaults', 'fmri');
spm_jobman('initcfg');

%% ========== USER INPUTS ==========
% Define your data paths
data_dir = '/Users/marcusdaghlian/CVL Dropbox/Marcus  Daghlian/pilot-clean/derivatives/spm_align/sub-01';  % Change this to your data directory
output_dir = fullfile(data_dir, 'GLM_output');

% Define functional runs
func_files = {
    fullfile(data_dir, 'rrun1.nii');
    fullfile(data_dir, 'rrun2.nii');
    fullfile(data_dir, 'rrun3.nii')
};


taskcol_onsets = {
    [15 105 135, 225];      % Run 1: onsets in seconds
    [15 105 135, 225];      
    [15 105 135, 225];      
};
task_durations = {
    [10, 10, 10];         % Run 1: durations in seconds
    [10, 10, 10];
    [10, 10, 10];
};



taskbw_onsets = {
    [45 75 165, 195];      % Run 1: onsets in seconds
    [45 75 165, 195]; 
    [45 75 165, 195];       
};


% Scanning parameters
TR = 3;  % Repetition time in seconds
n_slices = 90;  % Number of slices

%% ========== CREATE OUTPUT DIRECTORY ==========
if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

%% ========== SETUP SPM BATCH ==========
matlabbatch = {};

% Model specification
matlabbatch{1}.spm.stats.fmri_spec.dir = {output_dir};
matlabbatch{1}.spm.stats.fmri_spec.timing.units = 'secs';
matlabbatch{1}.spm.stats.fmri_spec.timing.RT = TR;
matlabbatch{1}.spm.stats.fmri_spec.timing.fmri_t = n_slices;
matlabbatch{1}.spm.stats.fmri_spec.timing.fmri_t0 = n_slices/2;

% Loop through runs
for run = 1:length(func_files)
    % Expand 4D nifti to individual volumes
    vols = spm_select('ExtFPList', fileparts(func_files{run}), ...
                      ['^' spm_file(func_files{run}, 'filename') '$'], Inf);
    
    % Session-specific setup
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).scans = cellstr(vols);
    
    % Task 1 condition
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(1).name = 'Col';
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(1).onset = taskcol_onsets{run};
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(1).duration = task_durations{run};
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(1).tmod = 0;
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(1).pmod = struct('name', {}, 'param', {}, 'poly', {});
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(1).orth = 1;
    
    % Task 2 condition
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(2).name = 'Bw';
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(2).onset = taskbw_onsets{run};
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(2).duration = task_durations{run};
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(2).tmod = 0;
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(2).pmod = struct('name', {}, 'param', {}, 'poly', {});
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).cond(2).orth = 1;
    
    % Multiple regressors (if you have motion parameters)
    %matlabbatch{1}.spm.stats.fmri_spec.sess(run).multi_reg = {fullfile(data_dir, ['rp_run' num2str(run) '.txt'])};
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).multi_reg = {''};
    
    % High-pass filter
    matlabbatch{1}.spm.stats.fmri_spec.sess(run).hpf = 128;
end

% Basis functions
matlabbatch{1}.spm.stats.fmri_spec.fact = struct('name', {}, 'levels', {});
matlabbatch{1}.spm.stats.fmri_spec.bases.hrf.derivs = [0 0];
matlabbatch{1}.spm.stats.fmri_spec.volt = 1;
matlabbatch{1}.spm.stats.fmri_spec.global = 'None';
matlabbatch{1}.spm.stats.fmri_spec.mthresh = 0.8;
matlabbatch{1}.spm.stats.fmri_spec.mask = {''};
matlabbatch{1}.spm.stats.fmri_spec.cvi = 'AR(1)';

%% ========== MODEL ESTIMATION ==========
matlabbatch{2}.spm.stats.fmri_est.spmmat = {fullfile(output_dir, 'SPM.mat')};
matlabbatch{2}.spm.stats.fmri_est.write_residuals = 0;
matlabbatch{2}.spm.stats.fmri_est.method.Classical = 1;

%% ========== CONTRAST SPECIFICATION ==========
matlabbatch{3}.spm.stats.con.spmmat = {fullfile(output_dir, 'SPM.mat')};

% Contrast 1: Task1 > baseline
matlabbatch{3}.spm.stats.con.consess{1}.tcon.name = 'Col > baseline';
matlabbatch{3}.spm.stats.con.consess{1}.tcon.weights = [1 0];
matlabbatch{3}.spm.stats.con.consess{1}.tcon.sessrep = 'replsc';

% Contrast 2: Task2 > baseline
matlabbatch{3}.spm.stats.con.consess{2}.tcon.name = 'Bw > baseline';
matlabbatch{3}.spm.stats.con.consess{2}.tcon.weights = [0 1];
matlabbatch{3}.spm.stats.con.consess{2}.tcon.sessrep = 'replsc';

% Contrast 3: Task1 > Task2
matlabbatch{3}.spm.stats.con.consess{3}.tcon.name = 'Col > Bw';
matlabbatch{3}.spm.stats.con.consess{3}.tcon.weights = [1 -1];
matlabbatch{3}.spm.stats.con.consess{3}.tcon.sessrep = 'replsc';

% Contrast 5: Effects of interest (F-contrast)
matlabbatch{3}.spm.stats.con.consess{5}.fcon.name = 'Effects of interest';
matlabbatch{3}.spm.stats.con.consess{5}.fcon.weights = eye(2);
matlabbatch{3}.spm.stats.con.consess{5}.fcon.sessrep = 'replsc';

matlabbatch{3}.spm.stats.con.delete = 0;

%% ========== RUN THE BATCH ==========
fprintf('Starting SPM GLM analysis...\n');
spm_jobman('run', matlabbatch);
fprintf('Analysis complete! Results saved to: %s\n', output_dir);

%% ========== RESULTS VIEWING (OPTIONAL) ==========
% Uncomment to automatically open results viewer
spm_results_ui('Setup', fullfile(output_dir, 'SPM.mat'));
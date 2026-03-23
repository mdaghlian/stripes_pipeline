function full_path_to_output = presurf_remove_background(full_path_to_uni, full_path_to_inv1, full_path_to_inv2, multiplyingFactor)
    %% ========================================================================
    %  FUNCTION: presurf_remove_background
    %  ========================================================================
    %  Removes "salt and pepper" background noise from MP2RAGE UNI image
    %  Based on RobustCombination method (O'Brien et al., 2014)
    %  Reference: https://doi.org/10.1371/journal.pone.0099676
    % Adapted from: 
    % https://github.com/khanlab/mp2rage_genUniDen.git
    disp(' ');
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp([datestr(datetime('now')), '        Removing Background Noise']);
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp(' ');
    
    if nargin < 4
        multiplyingFactor= 6; % Default = 6
    end
    
    %% Check SPM
    spm_directory = presurf_helper.check_spm_path();
    
    %% Handle inputs
    if nargin < 1 || isempty(full_path_to_uni)
        [uni_file_name, uni_file_path] = uigetfile('*.nii;*.nii.gz', 'Select UNI image');
        full_path_to_uni = fullfile(uni_file_path, uni_file_name);
    end
    
    if nargin < 2 || isempty(full_path_to_inv1)
        [inv1_file_name, inv1_file_path] = uigetfile('*.nii;*.nii.gz', 'Select INV1 image');
        full_path_to_inv1 = fullfile(inv1_file_path, inv1_file_name);
    end
    
    if nargin < 3 || isempty(full_path_to_inv2)
        [inv2_file_name, inv2_file_path] = uigetfile('*.nii;*.nii.gz', 'Select INV2 image');
        full_path_to_inv2 = fullfile(inv2_file_path, inv2_file_name);
    end
    
    disp(['> UNI: ', full_path_to_uni]);
    disp(['> INV1: ', full_path_to_inv1]);
    disp(['> INV2: ', full_path_to_inv2]);
    disp(['> multiplyingFactor: ', num2str(multiplyingFactor)]);
    
    %% Unzip if needed
    [uni_file_path, uni_file_prefix, uni_ext] = fileparts(full_path_to_uni);
    full_path_to_uni = presurf_helper.unzip_if_needed(full_path_to_uni, uni_file_path, uni_file_prefix, uni_ext);
    [~, uni_file_prefix, ~] = fileparts(full_path_to_uni);
    
    [inv1_file_path, inv1_file_prefix, inv1_ext] = fileparts(full_path_to_inv1);
    full_path_to_inv1 = presurf_helper.unzip_if_needed(full_path_to_inv1, inv1_file_path, inv1_file_prefix, inv1_ext);
    
    [inv2_file_path, inv2_file_prefix, inv2_ext] = fileparts(full_path_to_inv2);
    full_path_to_inv2 = presurf_helper.unzip_if_needed(full_path_to_inv2, inv2_file_path, inv2_file_prefix, inv2_ext);
    
    %% Load images
    disp('++++ Loading images...');
    UNI_nii = spm_vol(full_path_to_uni);
    MP2RAGEimg = spm_read_vols(UNI_nii);
    
    INV1_nii = spm_vol(full_path_to_inv1);
    INV1img = spm_read_vols(INV1_nii);
    
    INV2_nii = spm_vol(full_path_to_inv2);
    INV2img = spm_read_vols(INV2_nii);
    
    %% RobustCombination algorithm
    disp('++++ Applying RobustCombination algorithm...');
    
    % copied from Khan Lab github 
    % which in turn states...
    % adapted from RobustCombination function from Jose Marques, https://github.com/JosePMarques/MP2RAGE-related-scripts
    % this function shows one possible implementation of the methods suggested
    % in http://journals.plos.org/plosone/article?id=10.1371/journal.pone.0099676
%% defines relevant functions

MP2RAGErobustfunc  =@(INV1,INV2,beta)(conj(INV1).*INV2-beta)./(INV1.^2+INV2.^2+2*beta);

rootsquares_pos  =@(a,b,c)(-b+sqrt(b.^2 -4 *a.*c))./(2*a);
rootsquares_neg  =@(a,b,c)(-b-sqrt(b.^2 -4 *a.*c))./(2*a);

if and(min(MP2RAGEimg(:))>=0,max(MP2RAGEimg(:))>=0.51)
    % converts MP2RAGE to -0.5 to 0.5 scale - assumes that it is getting only
    % positive values
    MP2RAGEimg=(double(MP2RAGEimg)- max(double(MP2RAGEimg(:)))/2)./max(double(MP2RAGEimg(:)));
    integerformat=1;
    
else
    integerformat=0;
end

%% computes correct INV1 dataset  
INV2img=double(INV2img);

%gives the correct polarity to INV1;
INV1img=sign(MP2RAGEimg).*double(INV1img);

%
% because the MP2RAGE INV1 and INV2 is a summ of squares data, while the
% MP2RAGEimg is a phase sensitive coil combination.. some more maths has to
% be performed to get a better INV1 estimate which here is done by assuming
% both INV2 is closer to a real phase sensitive combination


INV1pos=rootsquares_pos(-MP2RAGEimg,INV2img,-INV2img.^2.*MP2RAGEimg);
INV1neg=rootsquares_neg(-MP2RAGEimg,INV2img,-INV2img.^2.*MP2RAGEimg);


INV1final=INV1img;
INV1final(abs(INV1img-INV1pos)> abs(INV1img-INV1neg))=INV1neg(abs(INV1img-INV1pos)>abs(INV1img-INV1neg));
INV1final(abs(INV1img-INV1pos)<=abs(INV1img-INV1neg))=INV1pos(abs(INV1img-INV1pos)<=abs(INV1img-INV1neg));


noiselevel=multiplyingFactor*mean(mean(mean(INV2img(1:end,end-10:end,end-10:end))));


UNI_denoised=MP2RAGErobustfunc(INV1img,INV2img,noiselevel.^2);
% UNI_denoised=MP2RAGErobustfunc(INV1final,INV2img,noiselevel.^2);
UNI_denoised=round(4095*(UNI_denoised+0.5));
    %% Save output
    INV1_nii.fname = fullfile(inv1_file_path, [inv1_file_prefix, '_adjusted.nii']);
    INV1_nii.descrip = sprintf('INV1 generated in course of MP2RAGE background removed, multiplyingFactor=%.2f', multiplyingFactor);
    spm_write_vol(INV1_nii, INV1final);


    UNI_nii.fname = fullfile(uni_file_path, [uni_file_prefix, '_denoised.nii']);
    UNI_nii.descrip = sprintf('MP2RAGE background removed, multiplyingFactor=%.2f', multiplyingFactor);
    spm_write_vol(UNI_nii, UNI_denoised);
    
    full_path_to_output = UNI_nii.fname;
    
    disp(' ');
    disp(['> Output: ', full_path_to_output]);
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp([datestr(datetime('now')), '        Completed Background Removal']);
    disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
    disp(' ');
    disp('NOTE: If background still has noise, increase regularization parameter.');
    disp('      If image has too much bias field, decrease regularization parameter.');
    disp(' ');
end
# Need to make scanner outputs bidsish 

```bash
dcm2nix /path/to/files
```

Copy .nii files & jsons to appropriate folder 

sub-##/
    anat/ 
    func/ 

For functional run s00_BIDsish, or adapt as necessary to get run numbers sensible

For anat - check .json files and name accordingly 

sub-##_acq-MP2RAGE_T1map -> for derived T1
& similarly for inv-1, inv-2, UNI
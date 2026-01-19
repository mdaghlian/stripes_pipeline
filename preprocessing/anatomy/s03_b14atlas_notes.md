# s03 generate b14 atlas for the freesurfer output

[1] Create conda env with neuropythy installed
```bash
mamba create -n b14atlas python
conda activate b14atlas
pip install neuropythy
```

[2] activate & run 
```bash
conda activate b14atlas
python s03_b14atlas.py sub-01 --fsdir /Users/marcusdaghlian/pilot-clean-link/derivatives/freesurfer
```

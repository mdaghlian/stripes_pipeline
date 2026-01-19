#!/usr/bin/env python
import os
import argparse
import numpy as np
import nibabel as nib

def create_benson14_labels(sub, fsdir):
    """Extract Benson14 ROI labels directly from .mgz files."""
    
    B14_AREAS = {
        1: 'V1',   2: 'V2',   3: 'V3',   4: 'hV4',
        5: 'VO1',  6: 'VO2',  7: 'LO1',  8: 'LO2',
        9: 'TO1', 10: 'TO2', 11: 'V3b', 12: 'V3a',
    }
    
    print(f'Processing {sub}')
    
    surf_dir = os.path.join(fsdir, sub, 'surf')
    label_dir = os.path.join(fsdir, sub, 'label', 'custom')
    os.makedirs(label_dir, exist_ok=True)
    
    # Check/generate Benson14 atlas if needed
    varea_files = [os.path.join(surf_dir, f'{h}.benson14_varea.mgz') 
                   for h in ['lh', 'rh']]
    
    if not all(os.path.exists(f) for f in varea_files):
        print(f"Generating Benson14 atlas...")
        os.system(f'python -m neuropythy atlas {sub} --verbose')
    
    # Process each hemisphere
    for hemi in ['lh', 'rh']:
        varea_file = os.path.join(surf_dir, f'{hemi}.benson14_varea.mgz')
        
        if not os.path.exists(varea_file):
            print(f'  Warning: {varea_file} not found')
            continue
        
        # Load varea data directly
        varea_data = nib.load(varea_file).get_fdata().squeeze()
        n_vertices = len(varea_data)
        
        # Create label header
        header = f'#!ascii label  , from sub {sub} vox2ras=TkReg\n'
        
        # Create individual ROI labels
        for area_id, area_name in B14_AREAS.items():
            vertices = np.where(varea_data == area_id)[0]
            
            if len(vertices) > 0:
                label_file = os.path.join(label_dir, f'{hemi}.b14_{area_name}.label')
                with open(label_file, 'w') as f:
                    f.write(header)
                    f.write(f'{len(vertices)}\n')
                    for v in vertices:
                        # Format: vertex_id x y z value
                        f.write(f'{v}  0.000  0.000  0.000  {area_id}\n')
        
        # Create combined ALL label
        all_vertices = np.where(np.isin(varea_data, list(B14_AREAS.keys())))[0]
        all_file = os.path.join(label_dir, f'{hemi}.b14_ALL.label')
        with open(all_file, 'w') as f:
            f.write(header)
            f.write(f'{len(all_vertices)}\n')
            for v in all_vertices:
                area_val = int(varea_data[v])
                f.write(f'{v}  0.000  0.000  0.000  {area_val}\n')
        
        print(f'  Created {hemi} labels ({len(all_vertices)} total vertices)')


def main():
    parser = argparse.ArgumentParser(
        description='Extract Benson14 ROI labels directly from .mgz files'
    )
    parser.add_argument('sub', help='sub ID (e.g., sub-01)')
    parser.add_argument('-d', '--fsdir', 
                       default=os.environ.get('subS_DIR', ''),
                       help='FreeSurfer subs directory')
    
    args = parser.parse_args()
    
    if not args.fsdir:
        parser.error('Set $subS_DIR or use --fsdir')
    
    create_benson14_labels(args.sub, args.fsdir)
    print('Done!')


if __name__ == '__main__':
    main()
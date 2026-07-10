#!/bin/bash
# Make different $PYPACKAGE_MANAGER environments we will use
echo "creating environments using ${PYPACKAGE_MANAGER}"
ENV_NAME="stripes"

if $PYPACKAGE_MANAGER env list | grep -q "^$ENV_NAME "; then
    echo "Environment '$ENV_NAME' found. Removing it..."
    $PYPACKAGE_MANAGER env remove -n $ENV_NAME -y
else
    echo "Environment '$ENV_NAME' does not exist. Skipping removal."
fi

$PYPACKAGE_MANAGER create -n $ENV_NAME python=3.10 -y
$PYPACKAGE_MANAGER run -n $ENV_NAME pip install -e $PIPELINE_DIR/cvl_utils
echo "Done! Activate with: $PYPACKAGE_MANAGER activate $ENV_NAME"

$PYPACKAGE_MANAGER run -n $ENV_NAME pip install \
    pycortex==$PYCTX_VERSION \
    nibabel==$NIBABEL_VERSION \
    nilearn==$NILEARN_VERSION \
    git+https://github.com/mdaghlian/dpu_mini.git \
    git+https://github.com/cvnlab/GLMsingle.git

echo $PYPACKAGE_MANAGER run -n $ENV_NAME pip install -e $BIDS_DIR/code/stripes_pipline/src/achstripes
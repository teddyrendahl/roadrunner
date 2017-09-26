#!/bin/bash
source /reg/neh/home/trendahl/conda/test_env.sh
source activate mfx
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}")" && pwd )"
python $DIR/start_block.py

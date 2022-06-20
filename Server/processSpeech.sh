#!/bin/bash

source /home/speech/kaldi/bin/activate
cd /home/speech/pykaldi/examples/setups/aspire/
source path.sh
cd /home/speech/


python3 /home/speech/python/preprocess.py

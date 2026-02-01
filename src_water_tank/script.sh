#!bin/bash
# how to run: sudo bash script.sh
# activate conda env
source /home/junjie/miniconda3/bin/activate /home/junjie/miniconda3/envs/pyclmuapp

echo "Starting run at: `date`"

# run the script
python script.py --n 400 --nproc 20 --container_type docker

echo "Ending run at: `date`"
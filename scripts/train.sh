#!/bin/bash

#SBATCH --job-name=train
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32GB
#SBATCH --time=30:59:00
#SBATCH --gres=gpu:rtx8000

source ~/.bashrc
conda activate sbi-fermi
cd /scratch/sm8383/sbi-fermi/
python -u train.py --sample train_float_all_ModelO --name gce_float_all_ModelO --batch_size 256


"""Sanity check: confirm GPU access from inside the current environment.

Inputs: none (reads the live torch/CUDA environment). Outputs: none written to
disk -- prints Python/host/PyTorch/CUDA/GPU details to stdout, exits nonzero if
no CUDA device is visible.

Position in the pipeline: not part of the result-generating pipeline itself --
a standalone pre-flight check, run via scripts/slurm/check_gpu.slurm before a
GPU job, to catch a missing CUDA module or a mismatched torch wheel before it
wastes a SLURM allocation.
"""
import torch
import sys
import platform

print(f"Python:           {sys.version.split()[0]}")
print(f"Hostname:         {platform.node()}")
print(f"PyTorch:          {torch.__version__}")
print(f"CUDA available:   {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA version:     {torch.version.cuda}")
    print(f"GPU count:        {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        print(f"GPU {i}:            {props.name} ({props.total_memory / 1e9:.1f} GB)")
else:
    print("ERROR: no CUDA. Check that you loaded a cuda module and "
          "installed the right torch wheel.")
    sys.exit(1)

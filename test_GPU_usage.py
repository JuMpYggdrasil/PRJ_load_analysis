import subprocess
import time

def check_gpu_usage():
    result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
    return "ollama" in result.stdout.lower()

print("GPU active:", check_gpu_usage())
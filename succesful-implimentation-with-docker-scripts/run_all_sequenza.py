import os
import subprocess
from pathlib import Path
import argparse
import sys

print("="*50)
print("Starting Sequenza Pipeline")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print("Environment variables:")
for key in ['BASE_DIR', 'SEQUENZA_OUTPUT', 'REFERENCE_FASTA', 'GC_WIGGLE', 'THREADS']:
    print(f"  {key}: {os.environ.get(key)}")

# Robust path handling with explicit validation
def resolve_path(env_var, default, must_exist=False):
    """Resolve path from environment variable with validation"""
    path_str = os.environ.get(env_var)
    if path_str:
        path = Path(path_str)
    else:
        path = Path(os.path.expanduser(default))
    
    print(f"Resolving {env_var}: {path}")
    
    if must_exist and not path.exists():
        print(f"ERROR: Path does not exist: {path}")
        sys.exit(1)
    
    return path

# Resolve paths
BASE_DIR = resolve_path('BASE_DIR', '~/test-work-sarek/WES-DNPM-RESULTS/preprocessing/recalibrated', must_exist=True)
SEQUENZA_OUTPUT = resolve_path('SEQUENZA_OUTPUT', '~/test-work-sarek/WES-DNPM-RESULTS/sequenza-output')
REFERENCE_FASTA = resolve_path('REFERENCE_FASTA', '~/whole-Exon-single-seq/ref-genome/index/hg19.fa', must_exist=True)
GC_WIGGLE = resolve_path('GC_WIGGLE', '~/whole-Exon-single-seq/ref-genome/sequenza-GC-wiggle/hg19.gc50Base.wig.gz', must_exist=True)
SEQUENZA_SCRIPT = Path('/app/sequenza_preprocess.py')  # Always in container
THREADS = int(os.environ.get('THREADS', 8))
BIN_WIDTH = 50

print("\nConfiguration Summary:")
print(f"BASE_DIR: {BASE_DIR} (exists: {BASE_DIR.exists()})")
print(f"SEQUENZA_OUTPUT: {SEQUENZA_OUTPUT} (exists: {SEQUENZA_OUTPUT.exists()})")
print(f"REFERENCE_FASTA: {REFERENCE_FASTA} (exists: {REFERENCE_FASTA.exists()})")
print(f"GC_WIGGLE: {GC_WIGGLE} (exists: {GC_WIGGLE.exists()})")
print(f"SEQUENZA_SCRIPT: {SEQUENZA_SCRIPT} (exists: {SEQUENZA_SCRIPT.exists()})")
print(f"THREADS: {THREADS}")
print(f"BIN_WIDTH: {BIN_WIDTH}")

# Create output directory
print("\nCreating output directory...")
try:
    SEQUENZA_OUTPUT.mkdir(parents=True, exist_ok=True)
    print(f"Successfully created directory: {SEQUENZA_OUTPUT}")
except Exception as e:
    print(f"ERROR: Failed to create directory {SEQUENZA_OUTPUT}: {str(e)}")
    sys.exit(1)

def find_sample_pairs(base_dir):
    """Find matched sample pairs by patient ID"""
    normals = {}
    tumours = {}
    pairs = []

    print(f"\nScanning for sample pairs in: {base_dir}")
    for folder in base_dir.iterdir():
        if folder.is_dir():
            name = folder.name
            if "Normal" in name:
                pid = name.replace("_Normal", "")
                normals[pid] = folder
                print(f"  Found Normal sample: {pid} at {folder}")
            elif "Tumour" in name or "Tumor" in name:
                pid = name.replace("_Tumour", "").replace("_Tumor", "")
                tumours[pid] = folder
                print(f"  Found Tumor sample: {pid} at {folder}")

    for pid in tumours:
        if pid in normals:
            pairs.append((pid, tumours[pid], normals[pid]))
            print(f"  Matched pair: {pid} (Tumor: {tumours[pid]}, Normal: {normals[pid]})")
        else:
            print(f"  WARNING: Tumor sample {pid} has no matching Normal")

    return pairs

def run_sequenza(pid, tumor_path, normal_path):
    """Run Sequenza preprocessing for one patient"""
    print(f"\n--- Processing {pid} ---")
    work_dir = SEQUENZA_OUTPUT / pid
    tumor_dir = work_dir / "preprocessing/recalibrated/Tumour"
    normal_dir = work_dir / "preprocessing/recalibrated/Normal"

    # Create working dirs
    print(f"Creating working directories for {pid}:")
    print(f"  Tumor dir: {tumor_dir}")
    print(f"  Normal dir: {normal_dir}")
    tumor_dir.mkdir(parents=True, exist_ok=True)
    normal_dir.mkdir(parents=True, exist_ok=True)

    # Symlink CRAM and CRAI files
    print("\nCreating symlinks for CRAM files:")
    for cram in tumor_path.glob("*.*"):
        if cram.suffix in ['.cram', '.crai']:
            target = tumor_dir / cram.name
            if not target.exists():
                print(f"  Linking: {cram} -> {target}")
                target.symlink_to(cram.resolve())
    
    for cram in normal_path.glob("*.*"):
        if cram.suffix in ['.cram', '.crai']:
            target = normal_dir / cram.name
            if not target.exists():
                print(f"  Linking: {cram} -> {target}")
                target.symlink_to(cram.resolve())

    # Run the sequenza_preprocess.py script
    cmd = [
        "python3", str(SEQUENZA_SCRIPT),
        "--sample", str(work_dir),
        "--fasta", str(REFERENCE_FASTA),
        "--gc", str(GC_WIGGLE),
        "--bin", str(BIN_WIDTH),
        "--threads", str(THREADS)
    ]
    print(f"\nRunning Sequenza command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print(f"✓ Completed: {pid}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error processing {pid}: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Sequenza analysis pipeline')
    parser.add_argument('--test', action='store_true', help='Process only the first sample pair')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    print("\nFinding sample pairs...")
    pairs = find_sample_pairs(BASE_DIR)
    print(f"Found {len(pairs)} matched Tumour-Normal sample pairs.")
    
    if args.test:
        print("\nRunning in TEST MODE (first sample only)")
        pairs = pairs[:1]

    success_count = 0
    for i, (pid, tumor, normal) in enumerate(pairs):
        print(f"\n{'='*50}")
        print(f"Processing pair {i+1}/{len(pairs)}: {pid}")
        print(f"  Tumor Path: {tumor}")
        print(f"  Normal Path: {normal}")
        if run_sequenza(pid, tumor, normal):
            success_count += 1

    print(f"\n{'='*50}")
    print(f"Processed {success_count}/{len(pairs)} sample pairs successfully")
    if success_count == len(pairs):
        print(" All samples processed successfully!")
        sys.exit(0)
    else:
        print(f" {len(pairs) - success_count} samples failed processing")
        sys.exit(1)

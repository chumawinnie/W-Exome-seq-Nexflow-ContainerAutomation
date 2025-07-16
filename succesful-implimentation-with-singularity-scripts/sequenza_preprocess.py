import os
import subprocess
from pathlib import Path
import argparse
import sys

def run_cmd(cmd, description):
    """Execute a command with detailed error handling"""
    print(f"\n[Running] {description}")
    print(" ".join(cmd))
    try:
        result = subprocess.run(cmd, check=True, stderr=subprocess.PIPE, text=True)
        return result
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        print(f" Command failed with exit code {e.returncode}:")
        print(f"   Command: {' '.join(e.cmd)}")
        print(f"   Error: {error_msg}")
        raise

def process_sample(sample_folder, reference_fasta, gc_wiggle, bin_width=50, threads=4):
    """Process a single sample through Sequenza pipeline"""
    try:
        print(f"\n{'='*50}")
        print(f"Starting Sequenza processing for: {sample_folder.name}")
        
        # Locate CRAM directories
        tumor_cram_dir = sample_folder / "preprocessing/recalibrated/Tumour"
        normal_cram_dir = sample_folder / "preprocessing/recalibrated/Normal"
        print(f"Tumor CRAM dir: {tumor_cram_dir}")
        print(f"Normal CRAM dir: {normal_cram_dir}")

        # Find CRAM files
        tumor_cram_file = next(tumor_cram_dir.glob("*.cram"), None)
        normal_cram_file = next(normal_cram_dir.glob("*.cram"), None)
        
        if not tumor_cram_file:
            print(f" Tumor CRAM file not found in {tumor_cram_dir}")
            return False
        if not normal_cram_file:
            print(f" Normal CRAM file not found in {normal_cram_dir}")
            return False

        print(f"Found Tumor CRAM: {tumor_cram_file}")
        print(f"Found Normal CRAM: {normal_cram_file}")

        # Prepare file paths
        tumor_bam = tumor_cram_file.with_suffix(".bam")
        normal_bam = normal_cram_file.with_suffix(".bam")
        sequenza_dir = sample_folder / "sequenza_files"
        sequenza_dir.mkdir(exist_ok=True)
        out_seqz = sequenza_dir / "out.seqz.gz"
        binned_seqz = sequenza_dir / "binned.out.seqz.gz"

        print(f"\nTemporary BAM files:")
        print(f"  Tumor BAM: {tumor_bam}")
        print(f"  Normal BAM: {normal_bam}")
        print(f"Output files:")
        print(f"  Raw Seqz: {out_seqz}")
        print(f"  Binned Seqz: {binned_seqz}")

        # Step 1: CRAM ➝ BAM
        run_cmd(
            ["samtools", "view", "-b", "-@", str(threads), 
             "-T", str(reference_fasta), 
             "-o", str(normal_bam), 
             str(normal_cram_file)],
            "Converting Normal CRAM to BAM"
        )
        run_cmd(
            ["samtools", "view", "-b", "-@", str(threads), 
             "-T", str(reference_fasta), 
             "-o", str(tumor_bam), 
             str(tumor_cram_file)],
            "Converting Tumor CRAM to BAM"
        )

        # Step 2: bam2seqz
        run_cmd(
            ["sequenza-utils", "bam2seqz",
             "-n", str(normal_bam),
             "-t", str(tumor_bam),
             "--fasta", str(reference_fasta),
             "-gc", str(gc_wiggle),
             "-o", str(out_seqz)],
            "Running bam2seqz"
        )

        # Step 3: Binning
        run_cmd(
            ["sequenza-utils", "seqz_binning",
             "--seqz", str(out_seqz),
             "-w", str(bin_width),
             "-o", str(binned_seqz)],
            "Running seqz_binning"
        )

        # Step 4: Clean up
        print("\nCleaning up temporary files...")
        for bam_file in [tumor_bam, normal_bam]:
            if bam_file.exists():
                bam_file.unlink()
                print(f"  Deleted: {bam_file}")
        
        print(f"\n Successfully processed {sample_folder.name}")
        print(f"Final output: {binned_seqz}")
        return True
        
    except Exception as e:
        print(f"\n Error processing sample: {str(e)}")
        # Clean up any partial files
        print("Cleaning up partial files...")
        for bam_file in [tumor_bam, normal_bam]:
            if 'bam_file' in locals() and bam_file.exists():
                bam_file.unlink()
                print(f"  Deleted partial: {bam_file}")
        return False
    except KeyboardInterrupt:
        print("\n Processing interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    print("="*50)
    print("Sequenza Preprocessing Script")
    print("="*50)
    
    parser = argparse.ArgumentParser(description="Run Sequenza preprocessing")
    parser.add_argument("--sample", required=True, help="Sample folder path")
    parser.add_argument("--fasta", required=True, help="Reference FASTA file")
    parser.add_argument("--gc", required=True, help="GC wiggle file")
    parser.add_argument("--bin", type=int, default=50, help="Bin width")
    parser.add_argument("--threads", type=int, default=4, help="Number of threads")
    
    args = parser.parse_args()
    
    try:
        sample_path = Path(args.sample).resolve()
        fasta_path = Path(args.fasta).resolve()
        gc_path = Path(args.gc).resolve()
        
        print(f"\nStarting Sequenza preprocessing for: {sample_path}")
        print(f"Using reference: {fasta_path}")
        print(f"Using GC wiggle: {gc_path}")
        print(f"Bin width: {args.bin}, Threads: {args.threads}")
        
        success = process_sample(sample_path, fasta_path, gc_path, args.bin, args.threads)
        if success:
            print("\n Processing completed successfully!")
            sys.exit(0)
        else:
            print("\n Processing failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n ‼FATAL ERROR: {str(e)}")
        sys.exit(1)

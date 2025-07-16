import os
import shutil
import gzip
import tempfile
from SigProfilerExtractor import sigpro as sig
from SigProfilerMatrixGenerator import install as genInstall
from SigProfilerAssignment import Analyzer as Analyze

def run_signature_extraction_from_sarek():
    # Base directory with original VCFs from Sarek
    base_dir = "/home/obiorach/test-work-sarek/WES-DNPM-RESULTS/variant_calling/mutect2"
    output_dir_base = "/home/obiorach/test-work-sarek/WES-DNPM-RESULTS/output-sig-result"
    os.makedirs(output_dir_base, exist_ok=True)

    print("Checking for GRCh37 genome installation...")
    genInstall.install('GRCh37')

    for patient_folder in os.listdir(base_dir):
        patient_vcf_dir = os.path.join(base_dir, patient_folder)
        if not os.path.isdir(patient_vcf_dir):
            continue

        for file in os.listdir(patient_vcf_dir):
            if file.endswith(".vcf.gz") and not file.endswith(".tbi"):
                original_vcf_path = os.path.join(patient_vcf_dir, file)
                print(f"Processing: {original_vcf_path}")

                try:
                    # Step 1: Create temp dir
                    with tempfile.TemporaryDirectory(prefix="vcf_tmp_", dir=patient_vcf_dir) as temp_dir:
                        print(f"Temporary directory created: {temp_dir}")

                        # Step 2: Decompress VCF
                        decompressed_vcf_path = os.path.join(temp_dir, file.replace(".gz", ""))
                        with gzip.open(original_vcf_path, 'rb') as f_in, open(decompressed_vcf_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                        print(f"Decompressed to: {decompressed_vcf_path}")

                        # Step 3: Output directory
                        sample_output_dir = os.path.join(output_dir_base, patient_folder)
                        os.makedirs(sample_output_dir, exist_ok=True)

                        # Step 4: Run signature extraction
                        sig.sigProfilerExtractor(
                            input_type="vcf",
                            input_data=temp_dir,
                            output=sample_output_dir,
                            minimum_signatures=1,
                            maximum_signatures=5,
                            nmf_replicates=100,
                            cpu=8
                        )
                        print(f"✓ Signature extraction completed for {patient_folder}")

                        # Step 5: Locate Samples.txt and run COSMIC fitting
                        samples_matrix = os.path.join(sample_output_dir, "SBS96", "Samples.txt")
                        if os.path.exists(samples_matrix):
                            Analyze.cosmic_fit(
                                samples=samples_matrix,
                                output=os.path.join(sample_output_dir, "SBS96"),
                                input_type="matrix",
                                context_type="SBS96",
                                genome_build="GRCh37",
                                exome=True
                            )
                            print(f"✓ COSMIC comparison completed for {patient_folder}")
                        else:
                            print(f"⚠ Samples.txt not found for {patient_folder}")

                except Exception as e:
                    print(f" Error processing {patient_folder}: {e}")

                print(f"Completed processing for {patient_folder}")
                print("-" * 80)

if __name__ == "__main__":
    run_signature_extraction_from_sarek()
    print("Script completed – created by Chuma Winner Obiora")

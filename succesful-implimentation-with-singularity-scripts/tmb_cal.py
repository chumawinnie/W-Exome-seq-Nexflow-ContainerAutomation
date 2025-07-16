import gzip
import os
import csv

# --- Settings ---
base_dir = os.path.expanduser("~/test-work-sarek/WES-DNPM-RESULTS/annotation/mutect2")
bed_file = os.path.expanduser("~/whole-Exon-single-seq/ref-genome/exom_targets.bed/HyperExomeV2_capture_targets.hg19.bed")
output_dir = os.path.expanduser("~/test-work-sarek/WES-DNPM-RESULTS/TMB-results")
os.makedirs(output_dir, exist_ok=True)

# Define consequence terms considered relevant for TMB
tmb_effects = {
    "missense_variant", "stop_gained", "stop_lost",
    "start_lost", "frameshift_variant", "inframe_insertion",
    "inframe_deletion", "splice_acceptor_variant", "splice_donor_variant"
}

# --- Functions ---
def get_coding_region_size(bed_path):
    total_bases = 0
    with open(bed_path, 'r') as bed_file:
        for line in bed_file:
            if line.strip() and not line.startswith("#"):
                parts = line.strip().split('\t')
                start = int(parts[1])
                end = int(parts[2])
                total_bases += end - start
    return total_bases / 1e6  # Convert to megabases

def count_tmb_mutations(vcf_path, effects_set):
    mutation_count = 0
    with gzip.open(vcf_path, 'rt') as f:
        for line in f:
            if line.startswith("#"):
                continue
            columns = line.strip().split("\t")
            filter_status = columns[6]
            if filter_status != "PASS":
                continue
            info = columns[7]
            csq_fields = [x for x in info.split(";") if x.startswith("CSQ=")]
            if csq_fields:
                csq_values = csq_fields[0].replace("CSQ=", "").split(",")
                for annotation in csq_values:
                    fields = annotation.split("|")
                    if len(fields) > 1 and fields[1] in effects_set:
                        mutation_count += 1
                        break  # Count once per variant
    return mutation_count

# --- Main pipeline ---
coding_region_mb = get_coding_region_size(bed_file)
summary_data = []

for folder in os.listdir(base_dir):
    folder_path = os.path.join(base_dir, folder)
    if os.path.isdir(folder_path):
        for file in os.listdir(folder_path):
            if file.endswith(".filtered_VEP.ann.vcf.gz"):
                vcf_file = os.path.join(folder_path, file)
                print(f"\n Processing: {vcf_file}")

                mutation_count = count_tmb_mutations(vcf_file, tmb_effects)
                tmb_value = mutation_count / coding_region_mb

                # Prepare result data
                result = {
                    "Sample": folder,
                    "NonSynonymousMutations": mutation_count,
                    "CodingRegionSize_Mb": f"{coding_region_mb:.2f}",
                    "TMB": f"{tmb_value:.2f}"
                }
                summary_data.append(result)

                # Write per-sample file
                output_file = os.path.join(output_dir, f"{folder}_TMB_Result.txt")
                with open(output_file, 'w') as out:
                    out.write(f"Sample: {folder}\n")
                    out.write(f"Total non-synonymous mutations (FILTER=PASS): {mutation_count}\n")
                    out.write(f"Coding region size: {coding_region_mb:.2f} Mb\n")
                    out.write(f"TMB-Score: {tmb_value:.2f} mutations/Mb\n")
                print(f" Result saved to {output_file}")

# --- Write summary CSV ---
summary_file = os.path.join(output_dir, "TMB_Summary.csv")
with open(summary_file, 'w', newline='') as csvfile:
    fieldnames = ["Sample", "NonSynonymousMutations", "CodingRegionSize_Mb", "TMB"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in summary_data:
        writer.writerow(row)

print(f"\n All results saved! Summary written to {summary_file}")
print("🎖️ Script developed by Chuma Winner Obiora, Bioinformatician @ Uni-Augsburg Bioinformatics Core Facility")

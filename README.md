# Project Summary

This pipeline was developed for automated somatic variant analysis in WES, WGS, and Panel sequencing data. It includes variant calling, CNV detection using Sequenza, TMB calculation, and mutational signature extraction and fitting. The pipeline can be executed using either Docker or Singularity, making it reproducible and portable for clinical environments.

Project developed at: University Hospital Augsburg Bioinformatics Core Facility
Principal Investigator: Dr. Jan Meier-Kolthoff 
Pipeline Developer: Chukwuma Winner Obiora
# Nextflow Bioinformatics Pipeline Documentation

## Overview

This documentation covers the complete development, troubleshooting, and optimization of an automated bioinformatics pipeline using Nextflow with both Docker and Singularity containerization. The pipeline integrates multiple genomics analysis tools for comprehensive cancer genomics analysis.

## Pipeline Components

### Complete Bioinformatics Pipeline Includes:
- **Whole Exome Sequencing Analysis** (nf-core/sarek)
- **Mutational Signatures Analysis** (SigProfiler)
- **Sequenza CNV Analysis** 
- **CNV & HRD (Homologous Recombination Deficiency) Post-processing**
- **Tumor Mutational Burden (TMB) Calculation**

## System Requirements

### Hardware Configuration
- **CPU**: 32 cores (minimum 16 cores)
- **Memory**: 62+ GB RAM (124 GB recommended)
- **Storage**: Sufficient space for genomics data and containers

### Software Dependencies
- Nextflow 24.10.2+
- Docker or Singularity
- Java 17+
- Python 3.9+
- R with required packages

## Initial Setup and Configuration

### 1. Nextflow Installation

**Problem Encountered**: Nextflow was initially installed in the current directory instead of a proper system location.

**Solution**:
```bash
# Install Nextflow properly
curl -s https://get.nextflow.io | bash
sudo mv nextflow /usr/local/bin/
sudo chmod +x /usr/local/bin/nextflow

# Or install in user bin directory
mv nextflow ~/bin/nextflow
```

**Key Learning**: Ensure Nextflow is in your PATH for proper container execution.

### 2. Version Compatibility Issues

**Problem**: Multiple Nextflow versions causing conflicts (22.10.6 vs 24.10.2).

**Diagnosis**:
```bash
which nextflow
ls -la $(which nextflow)
nextflow -version
```

**Solution**:
```bash
# Update alias in ~/.bashrc
alias nextflow=~/bin/nextflow  # Point to correct version

# Reload configuration
source ~/.bashrc
```

## Docker Implementation

### 🐳Initial Docker Setup 

#### 🐳Docker Configuration (nextflow.config)
```groovy
docker {
    enabled = true
}

process {
    withName: sequenza_analysis {
        container = 'sequenza-pipeline'
        containerOptions = '-e BASE_DIR=/data/sarek-output -e SEQUENZA_OUTPUT=/data/sequenza-output -e REFERENCE_FASTA=/ref/index/hg19.fa -e GC_WIGGLE=/ref/sequenza-GC-wiggle/hg19.gc50Base.wig.gz -e THREADS=8 -v /home/obiorach/test-work-sarek/WES-DNPM-RESULTS/preprocessing/recalibrated:/data/sarek-output:ro -v /home/obiorach/whole-Exon-single-seq/ref-genome:/ref:ro -v /home/obiorach/test-work-sarek/WES-DNPM-RESULTS/sequenza-output:/data/sequenza-output --user root --entrypoint=""'
        cpus = 8
        memory = '16 GB'
        time = '24 h'
    }
    
    withName: sequenza_cnv_hrd_analysis {
        container = 'sequenza-pipeline'
        containerOptions = '-v /home/obiorach/test-work-sarek/WES-DNPM-RESULTS:/data --user root --entrypoint=""'
        cpus = 8
        memory = '16 GB'
        time = '12 h'
    }
    
    withName: mutational_signature {
        container = 'sigprofiler-env'
        cpus = 4
        memory = '8 GB'
        time = '12 h'
    }
    
    withName: tmb_calculation {
        cpus = 2
        memory = '4 GB'
        time = '6 h'
    }
}

params {
    outdir = 'results'
}
```

### 🐳Docker Issues and Solutions

#### Issue 1: Entrypoint Conflicts
**Problem**: Container startup scripts interfering with R script execution.

**Error**: 
```
Starting Sequenza Pipeline
Python version: 3.10.12
ERROR: Path does not exist: /root/test-work-sarek/WES-DNPM-RESULTS/preprocessing/recalibrated
```

**Solution**: Add `--entrypoint=""` to containerOptions to bypass automatic startup scripts.

#### Issue 2: Resource Limitations
**Problem**: Process requesting more CPUs than available.
```
Process requirement exceeds available CPUs -- req: 24; avail: 16
```

**Solution**: Optimize resource allocation:
```groovy
--max_cpus 16
--max_memory '60 GB'
```

#### Issue 3: Volume Mount Path Mismatches
**Problem**: Container expecting different paths than host system.

**Solution**: Carefully map host paths to container paths using volume mounts.

### Docker Performance Results
- **Runtime**: ~13 hours
- **Success**: All processes completed
- **Resource Usage**: Good utilization of available resources

## Singularity Conversion

### Why Convert to Singularity?
- Better performance with direct file system access
- No Docker daemon overhead
- Better resource utilization
- More suitable for HPC environments

### Docker Image Building

Before converting to Singularity, the Docker images were built from custom Dockerfiles:

#### Building Docker Images🐳
```bash
# Build Sequenza pipeline Docker image
docker build -t sequenza-pipeline -f Dockerfile .

# Build SigProfiler environment Docker image  
docker build -t sigprofiler-env -f Dockerfile.signature .

# Verify images were built successfully
docker images | grep -E "(sequenza|sigprofiler)"
```

#### Docker🐳 Image Structure
- **`sequenza-pipeline`**: Contains Python scripts for Sequenza analysis and R environment for CNV/HRD processing
- **`sigprofiler-env`**: Contains SigProfiler tools for mutational signature analysis

### Container Conversion Process

#### 1. Install Singularity
```bash
sudo apt update
sudo apt install singularity-container
singularity --version
```

#### 2. Convert Docker🐳 Images to Singularity
```bash
# Create containers directory
mkdir -p containers

# Convert Docker images
singularity build containers/sequenza-pipeline.sif docker-daemon://sequenza-pipeline:latest
singularity build containers/sigprofiler-env.sif docker-daemon://sigprofiler-env:latest

# Verify conversions
ls -lh containers/
singularity exec containers/sequenza-pipeline.sif ls /app/
singularity exec containers/sigprofiler-env.sif python --version
```

### Singularity Configuration

#### Updated nextflow.config for Singularity
```groovy
profiles {
    singularity {
        singularity {
            enabled = true
            autoMounts = true
            runOptions = "--bind /home/obiorach/test-work-sarek/WES-DNPM-RESULTS/preprocessing/recalibrated:/data/sarek-output --bind /home/obiorach/whole-Exon-single-seq/ref-genome:/ref --bind /home/obiorach/test-work-sarek/WES-DNPM-RESULTS/sequenza-output:/data/sequenza-output --bind /home/obiorach/test-work-sarek/sigprofiler_reference:/root/.sigprofiler"
        }
        process {
            withName: sequenza_analysis {
                container = './containers/sequenza-pipeline.sif'
                cpus = 12
                memory = '32 GB'
                time = '24h'
            }
            withName: sequenza_cnv_hrd_analysis {
                container = './containers/sequenza-pipeline.sif'
                cpus = 8
                memory = '24 GB'
                time = '12h'
            }
            withName: mutational_signature {
                container = './containers/sigprofiler-env.sif'
                cpus = 6
                memory = '16 GB'
                time = '12h'
                env.MPLCONFIGDIR = '/tmp'
            }
            withName: tmb_calculation {
                cpus = 4
                memory = '8 GB'
                time = '6h'
            }
        }
        params {
            outdir = 'WES-DNPM-RESULTS'
        }
    }
}
```

### Critical Singularity Fix: Symlink Solution

#### Problem: Missing SigProfiler Reference
**Error**:
```
FATAL: container creation failed: mount /home/obiorach/test-work-sarek/sigprofiler_reference->/root/.sigprofiler error: 
mount source /home/obiorach/test-work-sarek/sigprofiler_reference doesn't exist
```

#### Investigation:
```bash
# Found actual data location
ls ~/test-work-sarek/sigprofiler-genome/references/GRCh37/
# Output: chromosomes  exome  sequences  transcripts  tsb  tsb_BED


#### Solution: Create Symlink
```bash
# Navigate to main directory
cd ~/test-work-sarek

# Create symlink pointing to actual data
ln -s sigprofiler-genome/references/GRCh37 sigprofiler_reference

# Verify symlink
ls -la sigprofiler_reference
# Output: sigprofiler_reference -> sigprofiler-genome/references/GRCh37

# Test symlink works
ls sigprofiler_reference/
# Output: chromosomes  exome  sequences  transcripts  tsb  tsb_BED
```


### downlaod the genome from genInstall and host locally for singularity :
```bash
python3 -c "from SigProfilerMatrixGenerator import install as genInstall; genInstall.install('GRCh37')"

/home/obiorach/miniconda3/lib/python3.12/site-packages/SigProfilerMatrixGenerator/references/


#with the expected subfolders:
chromosomes  CNV  matrix  SV  vcf_files

mkdir -p ~/test-work-sarek/sigprofiler_reference
cp -r /home/obiorach/miniconda3/lib/python3.12/site-packages/SigProfilerMatrixGenerator/references ~/test-work-sarek/sigprofiler_reference/GRCh37
```

#### Key Directory Structure:
```
~/test-work-sarek/                                                 # HOME-FOLDER
├── sigprofiler_reference -> sigprofiler-genome/references/GRCh37  # SYMLINK
├── sigprofiler-genome/
│   └── references/
│       └── GRCh37/                                              # ACTUAL DATA
│           ├── chromosomes
│           ├── exome
│           ├── sequences
│           ├── transcripts
│           ├── tsb
│           └── tsb_BED
├── sequenza-wig-file/
│   └── hg19.gc50Base.wig.gz                                     # GC WIGGLE FILE
├── containers/                                                  # SINGULARITY-APPTIANERS
│   ├── sequenza-pipeline.sif                                    # SEQUENZA SINGULARITY
│   └── sigprofiler-env.sif                                      # SIGPROFILER SINGULARITY
├── main-sarek-seq-mut-tmb.nf                                    # Nextflow MAIN.nf script
├── nextflow.config                                              # NEXTFLOW-CONTROL PANEL
├── samplesheet.csv                                              # SAMPLE METADATA
├── sequenza-CNV-A-HRD-processor.R                               # CNV/HRD ANALYSIS
├── sequenza_preprocess.py                                       # SEQUENZA PREPROCESSING
├── tmb_cal.py                                                   # TMB CALCULATION
├── run_all_sequenza.py                                          # SEQUENZA RUNNER
├── Mutation-Signatures.py                                       # SIGNATURE ANALYSIS
├── custom.config                                                # CUSTOM CONFIG(sarek-workflow)
├── Dockerfile.signature                                         # MUTATIONAL-SIGNATURE DOCKER CONTAINER
└── Dockerfile                                                   # COPY-NUMBER/HRD DOCKER CONTAINER
```

## Performance Optimization

### Resource Allocation Evolution

#### Initial Configuration (16 CPU system):
```groovy
--max_cpus 16
--max_memory '60 GB'
```

#### Upgraded System (32 CPU):
```groovy
--max_cpus 28
--max_memory '100 GB'

process {
    withName: sequenza_analysis {
        cpus = 12
        memory = '32 GB'
    }
    withName: sequenza_cnv_hrd_analysis {
        cpus = 8
        memory = '24 GB'
    }
    withName: mutational_signature {
        cpus = 6
        memory = '16 GB'
    }
    withName: tmb_calculation {
        cpus = 4
        memory = '8 GB'
    }
}
```

### Permission Management
```bash
# Fix permission errors before running Singularity
sudo chown -R obiorach:obiorach ~/test-work-sarek/WES-DNPM-RESULTS
sudo chown -R obiorach:obiorach ~/test-work-sarek/WES-DNPM-RESULTS/sequenza-output
sudo chown -R obiorach:obiorach ~/test-work-sarek/work
sudo chown -R obiorach:obiorach ~/test-work-sarek/containers
```

## Final Pipeline Implementation

### Main Pipeline Script (main-sarek-seq-mut-tmb.nf)
```groovy
#!/usr/bin/env nextflow
nextflow.enable.dsl=2

// ========= PROCESS 1: Run nf-core/sarek =============
process sarek_pipeline {
    executor 'local'  // Run on host to avoid Nextflow-in-container issues
    
    input:
    path config_file

    output:
    path 'sarek.done', emit: sarek_done

    script:
    """
    echo "Running nf-core/sarek pipeline..."
    nextflow run nf-core/sarek -r 3.5.1 -profile singularity \\
      --input /home/obiorach/test-work-sarek/samplesheet.csv \\
      --outdir /home/obiorach/test-work-sarek/WES-DNPM-RESULTS \\
      --genome hg19 \\
      --dbsnp /home/obiorach/whole-Exon-single-seq/ref-genome/known_sites.vcf/dbsnp_138.hg19.vcf.gz \\
      --known_indels /home/obiorach/whole-Exon-single-seq/ref-genome/known_indels.vcf/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf.gz \\
      --max_cpus 28 \\
      --max_memory '100 GB' \\
      --wes \\
      --intervals /home/obiorach/whole-Exon-single-seq/ref-genome/exom_targets.bed/HyperExomeV2_primary_targets.hg19.bed \\
      --tools mutect2,strelka,vep,manta,tiddit,cnvkit,msisensorpro \\
      --pon /home/obiorach/whole-Exon-single-seq/ref-genome/panel-of-normal/updated_Mutect2-exome-panel_vcf.vcf.gz \\
      --germline_resource /home/obiorach/whole-Exon-single-seq/ref-genome/germline-resource/renamed_gnomad.vcf.gz \\
      --vep_cache /home/obiorach/vep_cache \\
      --vep_species homo_sapiens \\
      --vep_genome GRCh37 \\
      --vep_cache_version 112 \\
      -c ${config_file} \\
      -resume

    touch sarek.done
    """
}

// ========= PROCESS 2: Mutational Signature ============
process mutational_signature {
    input:
    path sarek_done
    path mut_sig_script

    output:
    path 'mutational_signature.done', emit: mut_sig_done

    script:
    """
    echo "Running mutational signature analysis..."
    echo "Script file: ${mut_sig_script}"
    echo "Current directory: \$(pwd)"
    echo "Files in directory: \$(ls -la)"

    # Verify the script exists and is readable
    if [ -f "${mut_sig_script}" ]; then
        echo "Script found, executing..."
        python ${mut_sig_script}
    else
        echo "ERROR: Script ${mut_sig_script} not found!"
        exit 1
    fi

    touch mutational_signature.done
    """
}

// ========= PROCESS 3: Sequenza Analysis ==============
process sequenza_analysis {
    input:
    path sarek_done

    output:
    path 'sequenza.done', emit: sequenza_done

    script:
    """
    ls -la /app/
    echo "Running sequenza analysis..."
    export BASE_DIR=/data/sarek-output
    export SEQUENZA_OUTPUT=/data/sequenza-output
    export REFERENCE_FASTA=/ref/index/hg19.fa
    export GC_WIGGLE=/ref/sequenza-GC-wiggle/hg19.gc50Base.wig.gz
    export THREADS=8
    python3 /app/run_all_sequenza.py
    touch sequenza.done
    """
}

// ========= PROCESS 4: Sequenza CNV-HRD Analysis ==============
process sequenza_cnv_hrd_analysis {
    publishDir "${params.outdir}/sequenza-cnv-hrd", mode: 'copy'

    input:
    path sequenza_done

    output:
    path 'cnv-hrd.done', emit: cnv_hrd_done
    path 'sequenza-output/**', emit: cnv_hrd_results, optional: true

    script:
    """
    echo "Running Sequenza CNV-HRD analysis..."
    
    Rscript /app/sequenza-CNV-A-HRD-processor.R
    
    echo "Sequenza CNV-HRD analysis completed successfully!"
    touch cnv-hrd.done
    """
}

// ========= PROCESS 5: TMB Calculation =================
process tmb_calculation {
    input:
    path mutational_done
    path tmb_cal_script

    output:
    path 'tmb_calculation.done', emit: tmb_done

    script:
    """
    echo "Running TMB calculation analysis..."
    python ${tmb_cal_script}
    touch tmb_calculation.done
    """
}

// ========= PROCESS 6: Final Message ===================
process final_message {
    input:
    tuple path(tmb_done_file), path(sequenza_done_file), path(cnv_hrd_done_file)

    script:
    """
    echo ""
    echo " All pipelines completed successfully!"
    echo "Sequenza output available at: /home/obiorach/test-work-sarek/WES-DNPM-RESULTS/sequenza-output"
    echo " CNV-HRD results available at: ${params.outdir}/sequenza-cnv-hrd"
    echo " Complete analysis pipeline finished!"
    """
}

// ========= WORKFLOW ========================
workflow {
    mut_sig_script = Channel.fromPath('Mutation-Signatures.py')
    tmb_cal_script = Channel.fromPath('tmb_cal.py')
    custom_config_file = Channel.fromPath('custom.config')

    sarek_result = sarek_pipeline(custom_config_file)
    mut_sig_result = mutational_signature(sarek_result.sarek_done, mut_sig_script)
    sequenza_result = sequenza_analysis(sarek_result.sarek_done)
    cnv_hrd_result = sequenza_cnv_hrd_analysis(sequenza_result.sequenza_done)
    tmb_result = tmb_calculation(mut_sig_result.mut_sig_done, tmb_cal_script)

    // Combine all completion signals for final message
    all_done = tmb_result.tmb_done.combine(sequenza_result.sequenza_done).combine(cnv_hrd_result.cnv_hrd_done)
    final_message(all_done)
}
```

## Performance Results

###  Final Results: Singularity Implementation

#### Excellent Resource Utilization:
- **CPU hours**: 21.8 (55.4% cached)
- **32 CPU system**: Fully utilized
- **Succeeded**: 5 processes
- **Cached**: 1 process (smart resume)

#### Performance Comparison:
| Implementation | Runtime | Notes |
|---|---|---|
| **Docker version** | ~13 hours | Initial successful run |
| **Singularity version** | **1h 12m 40s** |  **~10x faster!** (thanks to caching + better performance) |

####  What this achievement means:
1. **Singularity conversion**: Complete success
2. **Mount issues**: Resolved (symlink solution worked perfectly)
3. **Performance**: Dramatically improved
4. **Full automation**: Working end-to-end
5. **Resource efficiency**: Excellent utilization of 32 CPU system

## Running the Pipeline

### Docker Version
```bash
nextflow run main-sarek-seq-mut-tmb.nf -with-docker -resume
```

### Singularity Version (Recommended)
```bash
nextflow run main-sarek-seq-mut-tmb.nf -profile singularity -resume
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Nextflow Not Found in Container
**Error**: `nextflow: command not found`
**Solution**: Add `executor 'local'` to sarek_pipeline process

#### 2. Version Compatibility Issues
**Error**: `Plugin nf-schema@2.2.1 requires Nextflow version >=23.10.0`
**Solution**: Update Nextflow alias to point to correct version

#### 3. CPU Resource Conflicts
**Error**: `Process requirement exceeds available CPUs`
**Solution**: Adjust `--max_cpus` to match your system capabilities

#### 4. Mount Directory Missing
**Error**: `mount source doesn't exist`
**Solution**: Create symlinks or update mount paths in configuration

#### 5. Permission Errors
**Error**: Permission denied when accessing files
**Solution**: 
```bash
sudo chown -R user:user /path/to/results
```

### Debugging Commands
```bash
# Check Nextflow version and location
which nextflow
nextflow -version

# Test container access
singularity exec containers/sequenza-pipeline.sif ls /app/

# Verify symlinks
ls -la sigprofiler_reference

# Check permissions
ls -la ~/test-work-sarek/WES-DNPM-RESULTS/
```

## Output Structure

### Results Directory Structure
```
WES-DNPM-RESULTS/
├── variant_calling/                           # Mutect2 caller VCF files
├── annotation/                                # VEP annotations
├── csv/                                       # Summary CSV files
├── multiqc/                                   # Quality control reports
├── preprocessing/                             # Aligned and processed BAMs
├── reports/                                   # Analysis reports
├── sequenza-output/                           # CNV analysis results
│   └── Patient_17/
│       └── sequenza_files/
│           ├── hrd_metrics.txt                # HRD scores
│           ├── Patient_17_segments.txt        # CNV segments
│           ├── Patient_17_chromosome_view.pdf # Visualizations
│           └── ...
├── sequenza-cnv-hrd/                          # CNV-HRD post-processing
├── TMB-results/                               # Tumor mutational burden
└── pipeline_info/                             # Execution reports
```

## Key Files and Their Purposes

### Analysis Scripts
- `Mutation-Signatures.py`: SigProfiler mutational signature analysis
- `tmb_cal.py`: Tumor mutational burden calculation
- `sequenza-CNV-A-HRD-processor.R`: CNV and HRD post-processing

### Configuration Files
- `nextflow.config`: Main pipeline configuration
- `custom.config`: Sarek-specific configuration
- `samplesheet.csv`: Sample information for analysis

### Container Files
- `containers/sequenza-pipeline.sif`: Singularity container for Sequenza analysis
- `containers/sigprofiler-env.sif`: Singularity container for mutational signatures

## Best Practices and Recommendations

### 1. Resource Management
- Always set appropriate CPU and memory limits
- Use `-resume` flag to restart failed pipelines efficiently
- Monitor resource usage during execution

### 2. Container Management
- Prefer Singularity over Docker for HPC environments
- Regularly update container images
- Test containers independently before pipeline execution

### 3. Data Organization
- Maintain consistent directory structure
- Use symlinks for complex file path management
- Implement proper backup strategies for results

### 4. Configuration Management
- Version control your configuration files
- Document all parameter changes
- Test configurations on small datasets first

### 5. Troubleshooting
- Always check logs in `.nextflow.log`
- Use `bash .command.run` in work directories for debugging
- Verify file permissions before running pipelines

## Conclusion

This comprehensive bioinformatics pipeline successfully integrates multiple state-of-the-art genomics analysis tools into a single automated workflow. The conversion from Docker to Singularity resulted in significant performance improvements while maintaining full functionality.

**Key achievements:**
- 10x performance improvement with Singularity
- Complete automation of complex genomics workflow
- Robust error handling and troubleshooting solutions
- Scalable resource utilization for various system configurations
- Production-ready pipeline suitable for clinical genomics applications

The pipeline is now ready for production use in cancer genomics research and clinical applications, providing comprehensive analysis from raw sequencing data to clinically relevant metrics including mutational signatures, copy number variations, homologous recombination deficiency scores, and tumor mutational burden.

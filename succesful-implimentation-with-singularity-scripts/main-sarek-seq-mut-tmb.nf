#!/usr/bin/env nextflow
nextflow.enable.dsl=2

// ========= PROCESS 1: Run nf-core/sarek =============
process sarek_pipeline {
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
      --max_cpus 20 \\
      --max_memory '30 GB' \\
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
    container 'sigprofiler-env'

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
    container 'sequenza-pipeline'

    input:
    path sarek_done

    output:
    path 'sequenza.done', emit: sequenza_done

    script:
    """
    #chmod +x /app/run_all_sequenza.py
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

// ========= PROCESS 4: TMB Calculation =================
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

// ========= PROCESS 5: Final Message ===================
process final_message {
    input:
    tuple path(tmb_done_file), path(sequenza_done_file)

    script:
    """
    echo ""
    echo "All pipelines completed successfully!"
    echo "Sequenza output available at: /home/obiorach/test-work-sarek/WES-DNPM-RESULTS/sequenza-output"
    echo "🎖️ Pipeline chain"
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
    tmb_result = tmb_calculation(mut_sig_result.mut_sig_done, tmb_cal_script)

    // Combine both completion signals for final message
    all_done = tmb_result.tmb_done.combine(sequenza_result.sequenza_done)
    final_message(all_done)
}

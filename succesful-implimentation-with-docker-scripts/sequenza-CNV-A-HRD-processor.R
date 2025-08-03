#!/usr/bin/env Rscript

###=====================================WARNING!=======================================================================
#devtools::install_github("buschlab/sequenza", build_vignettes = FALSE) sequenza installation!
#install_github('sztup/scarHRD',build_vignettes = TRUE) scar installation
#BiocManager::install("igordot/copynumber") copynumber installation
#Note all this is already handled by docker/singularity dependencies, use when runing without contianers e.g conda_env!
#=======================================WARNING!==========================================================================



# ======================== Load required libraries ========================
library(sequenza)
library(scarHRD)
library(copynumber)
library(knitr)
library(R.utils)
#library(devtools) removed not needed here!

# ======================== Define base directory ========================
base_dir <- "/data/sequenza-output"
patients <- list.dirs(base_dir, full.names = TRUE, recursive = FALSE)


# ======================== Iterate over each sample ========================
for (pat_dir in patients) {
  seq_dir <- file.path(pat_dir, "sequenza_files")
  seqz_gz <- file.path(seq_dir, "out.seqz.gz")
  seqz_file <- file.path(seq_dir, "out.seqz")
  sample_id <- basename(pat_dir)

  if (!file.exists(seqz_gz)) next
  if (file.exists(file.path(seq_dir, "hrd_metrics.txt"))) next

  message("Processing sample: ", sample_id)

  # Unzip .seqz.gz file
  gunzip(seqz_gz, destname = seqz_file, overwrite = TRUE, remove = FALSE)

  # Sequenza extract and fit. Note- Fit the Sequenza model to estimate purity/ploidy
  test <- sequenza.extract(seqz_file, verbose = FALSE)
  CP <- sequenza.fit(test)

  # Run results output to generate results and save them to the specified output directory
  sequenza.results(sequenza.extract = test, cp.table = CP,
                   sample.id = sample_id, out.dir = seq_dir)


  #===================== Results table (with descriptions) ===============================
  res_list <- c("alternative_fit.pdf", "alternative_solutions.txt",
                "chromosome_depths.pdf", "chromosome_view.pdf",
                "CN_bars.pdf", "confints_CP.txt",
                "CP_contours.pdf", "gc_plots.pdf",
                "genome_view.pdf", "model_fit.pdf",
                "mutations.txt", "segments.txt",
                "sequenza_cp_table.RData", "sequenza_extract.RData",
                "sequenza_log.txt")
  res_list <- paste(sample_id, res_list, sep = "_")

  description_list <- c(
    "Alternative solution fit to the segments. One solution per slide.",
    "List of all ploidy/cellularity alternative solutions.",
    "Coverage visualization in normal and tumor samples, before and after normalization.",
    "Chromosome view of depth ratio, B-allele frequency, and mutations. One chromosome per slide.",
    "Bar plot showing the percentage of genome in detected copy number states.",
    "Confidence interval table for the best solution from the model.",
    "Likelihood density for cellularity/ploidy solution with local maxima.",
    "GC correction visualization in normal and tumor samples.",
    "Genome-wide visualization of allele-specific and absolute copy number results.",
    "Model fit diagnostic plot.",
    "Table with mutation data and estimated number of mutated alleles (Mt).",
    "Table listing detected segments with copy number state estimates.",
    "RData file with maxima a posteriori computation.",
    "RData file of all sample information.",
    "Log with version and time information."
  )
  table_out <- data.frame(Files = res_list, Description = description_list)
  write.table(table_out, file = file.path(seq_dir, "result_description_table.tsv"),
              sep = "\t", quote = FALSE, row.names = FALSE)

  # ========================== Segment filtering and rounding =======================================
  seg_file <- file.path(seq_dir, paste0(sample_id, "_segments.txt"))
  alt_file <- file.path(seq_dir, paste0(sample_id, "_alternative_solutions.txt"))
  if (file.exists(seg_file) && file.exists(alt_file)) {
    seg.tab <- read.table(seg_file, header = TRUE, sep = "\t")
    alt_res <- read.table(alt_file, header = TRUE, sep = "\t", fileEncoding = "UTF-8")
    seg.tab <- seg.tab[seg.tab$CNt <= 4, ]
    is.num <- sapply(seg.tab, is.numeric)
    seg.tab[is.num] <- lapply(seg.tab[is.num], round, 3)
    write.table(seg.tab, file = file.path(seq_dir, "filtered_segments.tsv"), sep = "\t", row.names = FALSE)
  }

  # ======================================= Plots ========================================================================
  pdf(file.path(seq_dir, "genome_views.pdf"))
  try(sequenza:::genome.view(seg.tab), silent = TRUE)
  try(sequenza:::genome.view(seg.tab, info.type = "CNt"), silent = TRUE)
  dev.off()

  pdf(file.path(seq_dir, "raw_genome_view.pdf"))
  try(sequenza:::plotRawGenome(test, cellularity = alt_res$cellularity[1], ploidy = alt_res$ploidy[1]), silent = TRUE)
  dev.off()

  pdf(file.path(seq_dir, "CP_contours_plot.pdf"))
  try(cp.plot(CP), silent = TRUE)
  try(cp.plot.contours(CP, add = TRUE, likThresh = c(0.999, 0.95),
                       col = c("lightsalmon", "red"), pch = 20), silent = TRUE)
  dev.off()

  pdf(file.path(seq_dir, "chromosome_view.pdf"))
  try(chromosome.view(mut.tab = test$mutations[[1]],
                      baf.windows = test$BAF[[1]],
                      ratio.windows = test$ratio[[1]],
                      min.N.ratio = 1,
                      segments = test$segments[[1]],
                      main = test$chromosomes[1],
                      cellularity = alt_res$cellularity[1],
                      ploidy = alt_res$ploidy[1],
                      avg.depth.ratio = 1), silent = TRUE)
  dev.off()



  #======scarHRD-calculation========== :chr.in.names = FALSE when chr are numerical(1234...22 ) and  Calculate the HRD score using scarHRD with grch38 or grch37 as the reference genome

  hrd <- scar_score(seqz_file, reference = "grch37", seqz = TRUE, chr.in.names = TRUE)
  write.table(hrd, file = file.path(seq_dir, "hrd_metrics.txt"),
              sep = "\t", row.names = FALSE, quote = FALSE)

  # ============================ Clean up unzipped file ================================================
  file.remove(seqz_file)
}


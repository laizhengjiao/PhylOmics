# PhylOmics

**Phylogenomics analysis pipeline for multi-omics sequencing data**

---

```

      _______                    _        _______  _______ _________ _______  _______
     (  ____ )|\     /||\     /|( \      (  ___  )(       )\__   __/(  ____ \(  ____ \
     | (    )|| )   ( |( \   / )| (      | (   ) || () () |   ) (   | (    \/| (    \/
     | (____)|| (___) | \ (_) / | |      | |   | || || || |   | |   | |      | (_____
     |  _____)|  ___  |  \   /  | |      | |   | || |(_)| |   | |   | |      (_____  )
     | (      | (   ) |   ) (   | |      | |   | || |   | |   | |   | |            ) |
     | )      | )   ( |   | |   | (____/\| (___) || )   ( |___) (___| (____/\/\____) |
     |/       |/     \|   \_/   (_______/(_______)|/     \|\_______/(_______/\_______)

                                      PhylOmics v1.0
                               Phylogenomic Analysis Pipeline
``` 

---

## Overview

**phylomics** is an integrated phylogenomic analysis pipeline designed for **multi-omics sequencing data**, including:

- Genome sequencing (DNA)
- Transcriptome sequencing (RNA)

It supports **quality control, assembly, clustering, CDS/PEP prediction, BUSCO single-copy gene extraction**, and downstream phylogenomic preparation.

---

## Contact

- **Author**: Laizheng Jiao  
- **Email**: jlz0602@163.com  
- **ORCID**: 0009-0004-9204-1121  

---

## Usage

```
phylomics -mode <1|2|3> [Required Options] [Optional Options]
```

---

## Criticle pre-processing requirment

All input sequencing files **MUST** follow the standard directory structure:


folder_specified_by_rnaf/dnaf/  ────After Processing───→  folder_specified_by_rnaf/dnaf/
├── sample1_1.fq.gz             │              ├── sample1/
├── sample1_2.fq.gz             │              │   ├── sample1_1.fq.gz
├── sample2_1.fq.gz             │              │   └── sample1_2.fq.gz
└── sample2_2.fq.gz             │              └── sample2/
                                │                  ├── sample2_1.fq.gz
                                │                  └── sample2_2.fq.gz


- Each sample must be placed in an **independent subfolder**
- Paired-end reads must have explicit `_1` / `_2` suffix
- Supported formats:
  - `.fq`
  - `.fastq`
  - `.fq.gz`
  - `.fastq.gz`

If all paired-end sequencing files are located directly in the main directory (no subfolders), **run `phylomics -tidy <directory>` first** to organize them automatically.

---

## Core Modes

```
-mode 1   RNA only:
          QC → Assembly → CD-HIT → TransDecoder → CDS / PEP

-mode 2   RNA only:
          QC → Assembly → CD-HIT → rna_onlyass_result/ → BUSCO single-copy gene extraction

-mode 3   DNA only:
          QC → Assembly (SPAdes only) → CD-HIT → genome_assemble_result/ → BUSCO single-copy gene extraction
```

---

## BUSCO Parameter Rule (Mode 2 / Mode 3)

```
-clade <string>
```

- Specify BUSCO clade name **WITHOUT** `_odb12` suffix  
- The script automatically appends the suffix  
- To list available BUSCO databases:

```
busco --list-datasets
```

---

## Global Optional Parameters (All Modes)

```
-t <num>        Number of threads (default: 20)
-m <num>        Maximum memory in GB (default: 80)
-cleanfiles     Remove intermediate assembly files (default: OFF)
```

---

## Mode 1 / Mode 2 Exclusive Option

```
-assembler <tool>
```

- Transcriptome assembler
- Default: `spades` (rnaSPAdes)
- Supported options:
  - `spades`
  - `trinity`

---

## Independent Tidy Option (Run BEFORE Analysis)

```
-tidy <dir>
```

- Organize unstructured paired-end reads into sample subfolders
- **No other parameters allowed**
- Supported filename patterns:
  - `*_1/_2.fq`
  - `*_1/_2.fastq`
  - `*_1/_2.fq.gz`
  - `*_1/_2.fastq.gz`

---

## Usage Examples

### 1. Organize raw sequencing data

```
phylomics -tidy /data/raw_seq_data
```

---

### 2. Mode 1: Transcriptome assembly (default rnaSPAdes)

```
phylomics -mode 1 \
          -rnaf /data/processed_rna_seq \
          -t 16 \
          -m 64 \
          -cleanfiles
```

---

### 3. Mode 2: RNA assembly + BUSCO single-copy gene extraction

```
phylomics -mode 2 \
          -rnaf /data/processed_rna_seq \
          -clade piroplasmida \
          -t 16 \
          -m 64
```

---

### 4. Mode 3: Genome assembly + BUSCO analysis

```
phylomics -mode 3 \
          -dnaf /data/processed_dna_seq \
          -clade piroplasmida
```

---

## Main Invoked Software

| Software | Version | Reference |
|--------|--------|----------|
| fastp | v1.1.0 | Chen (2025) https://doi.org/10.1002/imt2.70078 |
| SPAdes | v4.2.0 | Prjibelski *et al.* (2020) https://doi.org/10.1002/cpbi.102 |
| rnaSPAdes | — | Bushmanova *et al.* (2019) https://doi.org/10.1093/gigascience/giz100 |
| Trinity | v2.15.2 | Grabherr *et al.* (2011) https://doi.org/10.1038/nbt.1883 |
| BUSCO | v5.8.3 | Tegenfeldt *et al.* (2025) https://doi.org/10.1093/nar/gkae987 |
| CD-HIT | v4.8.1 | Fu *et al.* (2012) https://doi.org/10.1093/bioinformatics/bts565 |
| TransDecoder | — | Haas BJ https://github.com/TransDecoder/TransDecoder|
| MAFFT | v7.526 | Katoh & Standley (2013) https://doi.org/10.1093/molbev/mst010 |
| trimAl | v1.5.1 | Capella-Gutiérrez et al. (2009) https://doi.org/10.1093/bioinformatics/btp348|
| IQ-TREE | v3.0.1 | Wong *et al.* (2025) https://doi.org/10.32942/X2P62N|
| FASconCAT-G | v1.06.1 | Kück & Longo (2014) https://doi.org/10.1186/s12983-014-0081-x|
| ASTER | v1.23 | Zhang *et al.* (2025) https://doi.org/10.1093/molbev/msaf172|
| OrthoFinder | v3.1.2 | Emms *et al.* (2025) https://doi.org/10.1101/2025.07.15.664860|

---

## Additional Scripts (Optional Citation)
The following scripts are integrated into the environment:
| Script | Version | Reference |
|--------|--------|----------|
| srr2organism | —  | Jiao (2026a) https://doi.org/10.5281/zenodo.18242837 |
| batch_alignment | —  | Jiao (2026b) https://doi.org/10.5281/zenodo.18345651 |
| batch_trimal | — | Jiao (2026b) https://doi.org/10.5281/zenodo.18345651 |
| batch_iqtree | —  | Jiao (2026b) https://doi.org/10.5281/zenodo.18345651 |
| SRASeqFetcher | —  | Jiao (2026c) https://doi.org/10.5281/zenodo.18281342 |
| FastqMerger | —  | Jiao (2026d) https://doi.org/10.5281/zenodo.18367708 |

```

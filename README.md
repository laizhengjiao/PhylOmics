# PhylOmics
Phylogenomics analysis pipeline for multi-omics sequencing data

============================================================================================

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
============================================================================================

PHYLOMICS: Phylogenomic analysis pipeline for multi-omics sequencing data (genome/transcriptome)
For any questions, please contact the author: Laizheng Jiao (jlz0602@163.com) (ORCID: 0009-0004-9204-1121)
Usage: phylomics -mode <1|2|3> [Required Options] [Optional Options]

CRITICAL PRE-ANALYSIS REQUIREMENT:
  All files under -rnaf (mode1/2) or -dnaf (mode3) MUST follow the standard format:
  - Each sample has an independent subfolder
  - Paired-end sequencing data in each subfolder with explicit _1/_2 suffix
  - Supported suffixes: .fq, .fastq, .fq.gz, .fastq.gz
  If all paired files are in the root of target dir (no subfolders), use -tidy FIRST (independently) to organize

Core Modes:
      -mode 1   only RNA: QC -> assembly -> cd-hit -> TransDecoder -> CDS/PEP

      -mode 2   only RNA: QC -> assembly -> cd-hit -> rna_onlyass_result/ -> BUSCO single-copy gene extraction

      -mode 3   only DNA: QC -> assembly (spades exclusive) -> cd-hit -> genome_assemble_result/ -> BUSCO single-copy gene extraction

Mode 2/3 BUSCO Parameter Rule:
      -clade <string>  Specify the clade name for BUSCO database (WITHOUT _odb12 suffix, script auto adds it)
                       To check available BUSCO databases, run: 'busco --list-datasets'

Optional Global Options (for all modes):
      -t <num>      Number of threads (default: 20)
      -m <num>      Maximum memory (GB, default: 80)
      -cleanfiles   Delete intermediate assembly files after analysis (default: off)

Mode 1/2 Exclusive Optional Option:
      -assembler <tool>  Assembler for transcriptome/RNA (default: spades/rnaspades)
                         Supported: spades, trinity

Independent Tidy Option (RUN FIRST BEFORE ANALYSIS):
      -tidy <dir>   Organize unstructured paired read files into sample folders (NO other parameters allowed)
                    Supports: *_1/_2.fq, *_1/_2.fastq, *_1/_2.fq.gz, *_1/_2.fastq.gz

Usage Examples:
   1. Tidy first (independent) - organize unstructured paired reads into sample folders
       phylomics -tidy /data/raw_seq_data

   2. Mode1: Transcriptome assembly (default rnaspades) with custom threads/memory
       phylomics -mode 1 -rnaf /data/processed_rna_seq -t 16 -m 64 -cleanfiles

   3. Mode2: RNA only assembly (default rnaspades) + BUSCO db download + batch BUSCO analysis, custom threads
       phylomics -mode 2 -rnaf /data/processed_rna_seq -clade piroplasmida -t 16 -m 64

   4. Mode3: Genome assembly + BUSCO (piroplasmida clade) with default parameters
       phylomics -mode 3 -dnaf /data/processed_dna_seq -clade piroplasmida

Main Invoked Software
       fastp v1.0.1         Please cite:  Chen (2025) https://doi.org/10.1002/imt2.70078
       SPAdes v4.0.0        Please cite:  Prjibelski et al., (2020) https://doi.org/10.1002/cpbi.102
       rnaSPAdes            Please cite:  Bushmanova et al., (2019) https://doi.org/10.1093/gigascience/giz100
       Trinity v2.15.2      Please cite:  Grabherr et al., (2011) https://doi.org/10.1038/nbt.1883
       BUSCO v5.8.3         Please cite:  Tegenfeldt et al., (2025) https://doi.org/10.1093/nar/gkae987
       CD-HIT v4.8.1        Please cite:  Fu et al., (2012) https://doi.org/10.1093/bioinformatics/bts565
       TransDecoder         Please cite:  Haas, BJ. https://github.com/TransDecoder/TransDecoder
       Trinity2Unigene      Please cite:  Feng et al., (2020) https://doi.org/10.1111/nph.16588
       MAFFT v7.525         Please cite:  Katoh and Standley, (2013) https://doi.org/10.1093/molbev/mst010
       trimAl v1.5.rev1     Please cite:  Capella-Gutiérrez et al., (2009) https://doi.org/10.1093/bioinformatics/btp348
       IQ-TREE v3.0.1       Please cite:  Wong et al., (2025) https://doi.org/10.32942/X2P62N
       FASconCAT-G v1.06.1  Please cite:  Kück and Longo (2014) https://doi.org/10.1186/s12983-014-0081-x
       ASTER v1.23.4.6      Please cite:  Zhang et al., (2025) https://doi.org/10.1093/molbev/msaf172
       OrthoFinder v3.1.2   Please cite:  Emms et al., (2025) https://doi.org/10.1101/2025.07.15.664860

We have compiled several analytical processing scripts in the environment.
If you find them useful, you could choose to cite them:
       srr2organism         Please cite:  Jiao (2026a) https://doi.org/10.5281/zenodo.18242837
       batch_alignment      Please cite:  Jiao (2026b) https://doi.org/10.5281/zenodo.18345651
       batch_trimal         Please cite:  Jiao (2026b) https://doi.org/10.5281/zenodo.18345651
       batch_iqtree         Please cite:  Jiao (2026b) https://doi.org/10.5281/zenodo.18345651
       SRASeqFetcher        Please cite:  Jiao (2026c) https://doi.org/10.5281/zenodo.18281342

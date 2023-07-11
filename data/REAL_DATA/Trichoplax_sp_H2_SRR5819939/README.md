Data source:
============

### Contigs FASTA: 

```diff
wget https://sra-download.ncbi.nlm.nih.gov/traces/wgs03/wgs_aux/GF/SF/GFSF01/GFSF01.1.fsa_nt.gz
gzip -d GFSF01.1.fsa_nt.gz
```

### Paired reads:

Use SRA Toolkit (https://github.com/ncbi/sra-tools/wiki) to download runs locally.

```diff
fastq-dump -X 5  --split-files  SRR5819939
https://www.ebi.ac.uk/ena/browser/view/SRR5819939

```

intronSeeker command lines
============================

### Step 1 : hisat2Alignment

```diff
intronSeeker hisat2Alignment -r GFSF01.1.fsa_nt -1 SRR5819939_1.fastq -2 SRR5819939_2.fastq --prefix GFSF01 -o GFSF01 -t 12
```

### Step2: splitReadSearch

```diff
intronSeeker splitReadSearch -a GFSF01/hisat2_GFSF01.sort.bam -r GFSF01.1.fsa_nt --prefix GFSF01 --output splitReadSearch_GFSF01
```

### Step 3: run simulation2HTML

Configuration file:

```diff
[Defaults]
fasta:GFSF01.1.fsa_nt
r1:SRR5819939_1.fastq
r2:SRR5819939_2.fastq
flagstat:hisat2_SRR5819939.sort.flagstat.txt
candidat:srs_SRR5819939_candidates.txt
split:srs_SRR5819939_split_alignments.txt
prefix:GFSF01
threads: 6                
output:HTML/
force: -F
```


```diff
python3 /PATH/TO/intronSeeker/scripts/simulation2HTML.py -F --config_file  SRR5819939.cfg;

```

HTML report is available in this directory.
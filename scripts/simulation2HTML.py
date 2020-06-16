#!/usr/bin/env python3

import os
import argparse 
from argparse import ArgumentParser
import configparser # To parse parameters file
import numpy as np  # For Split read signal analysis
import pandas as pd
import pysam   # To generate a dataframe from a BAM : pysam and pickle
import pickle
import glob
import time
import subprocess as sp # To run subprocess
import concurrent.futures as prl # For Split read signal analysis
from itertools import repeat     # For Split read signal analysis
# Import all functions from internal modules
from simulation2HTMLparse import *
from simulation2HTMLtags import *
from simulation2HTMLplots import *


# source activate ISeeker_environment;
# cd scripts/; 
# python3 simulation2HTML.py --config_file ../config/simulation2HTML_example.cfg -F 
# scp  /home/Sarah/Documents/PROJETS/INTRONSEEKER/FRS/CAS-A/sample1/HTML/*FRS_CASA_sample1_n1000_r_STAR*.html smaman@genologin.toulouse.inra.fr:/save/smaman/public_html/intronSeeker/.
# See result : http://genoweb.toulouse.inra.fr/~smaman/intronSeeker/report_FRS_CASA_sample1_n1000_r_STAR_simulation.html

############
# SUB MAIN #
############
def simulationReport(   config_file: str,fasta:str, mfasta:str, gtf:str, r1:str, r2:str, ranks:str,
                        flagstat:str, candidat:str, split:str,
                        output:str, prefix:str, force:bool, threads:int ) :

    output_path = output + "/report"
    if prefix:
        output_path += "_" + prefix

    # Create output dir if not exist
    if not os.path.exists(output) :
        os.makedirs(output)
    
    # Output path filename report html
    output_file = output_path + "_simulation.html"
    if not force:
        try :
            if os.path.exists(output_file):
                raise FileExistsError
        except FileExistsError as e :
            print('\nError: output file already exists.\n')
            exit(1)

    print("Output dir and report html")        

	### MEMO 
	# fasta  = sequences used to generate reads
	# mfasta = sequences used to align reads
	
	### Build pandas ###
    # df_fasta    : pandas.DataFrame where each line is a seq description from FASTA file
    # df_mfasta   : pandas.DataFrame where each line is a modified seq description from modified FASTA file
    # df_library  : pandas.DataFrame where each line is a read description from R1 (& R2) fastq file(s)
    # df_features : pandas.DataFrame where each line is a simulated features description 
    # df_candidat : pandas.DataFrame where each line is a candidat description
    df_fasta  = parse_fasta(fasta.name, False)
    df_mfasta = parse_fasta(mfasta.name, True)

    if r2 :
        df_library = parse_library(r1.name, r2.name)
    else :
        df_library = parse_library(r1.name)

    df_features = parse_gtf(gtf.name)

    # Add a column to df_fasta with the "fasta" length (without any simulated features)
    df_mfasta["short_length"] = df_mfasta.apply(
        compute_tr_length,
        axis = 1,
        df_features=df_features
    )
    
    # Add two columns to df_features:
    #  1- the true insertion position of the simulated feature (in term of mfasta length percentage)
    #  2- the borders of the simulated features (in term of nucleotides)
    df_features = df_features.join(
        other = df_features.apply(
            compute_pos_on_mfasta,
            axis=1,
            df_mfasta=df_mfasta
        )
    )

    print("Build pandas dataframes")  

    # HEADER
    html = get_html_header()
    
    inputfiles = [
        "Contig FASTA#" + os.path.basename(fasta.name),
        "Contig FASTA with feature(s)#" + os.path.basename(mfasta.name),
        "GTF of contig with feature(s)#" + os.path.basename(gtf.name),
        "Read1 FASTQ#" + os.path.basename(r1.name)
    ]
    if r2:
        inputfiles.append("Read2 FASTQ#" + os.path.basename(r2.name))
    ranks_file=""    
    if ranks:
        ranks_file=ranks.name
        inputfiles.append("Ranks#" + os.path.basename(ranks.name))
    flagstat_file = ""
    if flagstat :
        flagstat_file = flagstat.name
        inputfiles.append("Flagstat#" + os.path.basename(flagstat_file))
    split_file=""    
    if split:
        split_file=split.name
        inputfiles.append("Split#" + os.path.basename(split.name))
    candidat_file=""    
    if candidat:
        candidat_file=candidat.name
        inputfiles.append("Candidat#" + os.path.basename(candidat.name))

    html += get_html_body1(flagstat_file, split_file, candidat_file)

   
    # INPUT FILES
    html += get_html_inputfiles(inputfiles)
    print("List input files")

    # SEQUENCE STAT
    # Global stat
    nb_distinct_features, nb_ctg_by_feature, ctg_descr = stat_from_gtf(gtf.name)
    global_stat = dict()
    global_stat["0Contig FASTA - Number of seq."]            = df_fasta.shape[0]
    global_stat["1Contig FASTA - Mean seq. length"]          = int(df_fasta['length'].mean())
    global_stat["2Contig FASTA with feature(s) - Number of seq."]   = df_mfasta.shape[0]
    global_stat["3Contig FASTA with feature(s) - Mean seq. length"] = int(df_mfasta['length'].mean())
    global_stat["4Number of modified sequences"]           = df_mfasta.loc[df_mfasta.index.str.contains(".modif")].shape[0]
    global_stat["5Number of distinct features in GTF"]     = df_features.feature.value_counts().shape[0]
    global_stat["6Number of features in GTF"]              = df_features.shape[0]
    c = 7
    for k, v in (df_features.feature.value_counts()).items() :
        global_stat[str(c)+k] = v
        c+=1

    # ASSEMBLATHON on fasta files        
    nbContigs, totContigSize, longestContig, shortestContig, nbContigsSup1K, n50, l50, meanContigSize = run_assemblathon(fasta.name)
    global_stat_assemblathon_fasta = dict()
    global_stat_assemblathon_fasta["0Number of contigs"]         = nbContigs
    global_stat_assemblathon_fasta["1Mean contigs length"]       = round(meanContigSize, 0)
    global_stat_assemblathon_fasta["2Total size of contigs"]     = totContigSize
    global_stat_assemblathon_fasta["3Longest contig"]            = longestContig
    global_stat_assemblathon_fasta["4Shortest contiged"]         = shortestContig
    global_stat_assemblathon_fasta["5Number of contigs > 1K nt"] = nbContigsSup1K
    global_stat_assemblathon_fasta["6N50 contig length"]         = n50
    global_stat_assemblathon_fasta["7L50 contig count"]          = l50

    if mfasta:
        nbContigs, totContigSize, longestContig, shortestContig, nbContigsSup1K, n50, l50, meanContigSize = run_assemblathon(mfasta.name)
        global_stat_assemblathon_mfasta = dict()
        global_stat_assemblathon_mfasta["0Number of contigs"]         = nbContigs
        global_stat_assemblathon_mfasta["1Mean contigs length"]       = round(meanContigSize, 0)
        global_stat_assemblathon_mfasta["2Total size of contigs"]     = totContigSize
        global_stat_assemblathon_mfasta["3Longest contig"]            = longestContig
        global_stat_assemblathon_mfasta["4Shortest contiged"]         = shortestContig
        global_stat_assemblathon_mfasta["5Number of contigs > 1K nt"] = nbContigsSup1K
        global_stat_assemblathon_mfasta["6N50 contig length"]         = n50
        global_stat_assemblathon_mfasta["7L50 contig count"]          = l50

    html += get_html_seq_descr(global_stat, nb_ctg_by_feature, ctg_descr, gtf.name, df_features['pos_on_contig'], df_fasta, df_mfasta, global_stat_assemblathon_fasta, global_stat_assemblathon_mfasta)
    print("Global statistics")

    # # READS STAT    TODO : à remettre
    # # Global stat
    # global_stat_fastq = dict()
    # global_stat_fastq["0Number of reads"] = df_library['contig'].count()
    # global_stat_fastq["1Mean coverage"] = 0
    # for i,row in df_library.iterrows():
    #     global_stat_fastq["1Mean coverage"] += row['end'] - row['start'] + 1
    # global_stat_fastq["1Mean coverage"] /= (global_stat["1Contig FASTA - Mean seq. length"] * global_stat["0Contig FASTA - Number of seq."])
    # meanCoverage = round(global_stat_fastq["1Mean coverage"], 2)
    # global_stat_fastq["1Mean coverage"] = meanCoverage
    # global_stat_fastq["2Min reads length"] = df_features['length'].min()  #TODO
    # global_stat_fastq["3Max reads length"] = df_features['length'].max()
    # global_stat_fastq["4Mean reads length"] = round(df_features['length'].mean())
      
    # html += get_html_reads_descr(global_stat_fastq) 
    # print("Reads statistics")

    # ABUNDANCE number of reads by contig
    # Build a dataframe with:
    #   ctg
    #   abund_perc => (number of read on this contig / number of reads) * 100
    #   requested  => if grinder ranks output file is given ...
    #   norm       => (((number of read on this contig / contig len) * mean len of all contigs) / number of reads) * 100
    df_tmp = pd.DataFrame((df_library.groupby('contig').size()/len(df_library))*100, columns = ['abund_perc'])
    df_fasta = df_fasta.assign(real=df_tmp.abund_perc.values)
    if ranks:
        df_tmp = parse_rank_file(ranks_file)
        df_fasta = df_fasta.assign(rank=df_tmp['rank'].values)
        df_fasta = df_fasta.assign(waiting=df_tmp.rel_abund_perc.values)
    df_tmp = pd.DataFrame(
        (((df_library.groupby('contig').size()/df_fasta['length'])*(df_fasta['length'].mean()))/df_library.shape[0])*100,
        columns = ['norm'])
    df_fasta = df_fasta.assign(norm=df_tmp['norm'].values)
    del df_tmp
    #html += get_html_abundance(df_fasta)  TODO : a remettre
    print("Abundance")
   
    ## ALIGNMENT STATS
    if flagstat:
        nbreads, mapped, paired, proper, secondary, singletons=parse_flagstat(flagstat_file)

        global_stat_flagstat = dict()
        global_stat_flagstat["0Number of mapped"] = mapped
        global_stat_flagstat["1Number of properly paired reads"] = proper
        global_stat_flagstat["2Number of unmapped reads (nb QC passed - nb mapped)"] = int(nbreads) - int(mapped)
        global_stat_flagstat["3Secondary"] = secondary
        global_stat_flagstat["4Singletons"] = singletons

        html += get_html_flagstat_descr(global_stat_flagstat)
   
    html += get_html_results()
    print("Mapping statistics")
   
    ## SPLITREADSEARCH STAT
    if split:
        df_split=parse_split(split.name)   
        global_stat_split = dict()
        global_stat_split["0Number of reads overlapping introns"]= df_split.shape[0]
        global_stat_split["1Mean length of introns"]= df_split['split_length'].mean()

        nbCanonic = 0
        nbOtherJunctions = 0
        df_split.sort_values(by=['split_borders'])
        c = 2
        n = 0
        for k, v in (df_split['split_borders'].value_counts()).items() :
            if k == "GT_AG" or k == "CT_AC":
                nbCanonic += v
            elif n < 11:
                global_stat_split[str(c)+"Junction "+k] = v
                n += 1
                c += 1
            else:
                nbOtherJunctions += v
        global_stat_split[str(c)+"Other junctions"] = nbOtherJunctions
        global_stat_split[str(c+1)+"Canonical junction (GT_AG or CT_AC)"] = nbCanonic
        
        html += get_html_split_descr(global_stat_split)   
        print("Intron reads") 

    ## CANDIDATS statistics - detected introns
    if candidat:
        df_candidat, mindepth, maxlen = parse_candidat(candidat.name)

         # Definition dict
        definitions = dict()
        definitions['DP']   = "Filtered because of depth (<= "+ str(mindepth)+ ")"
        definitions['LEN']  = "Filtered because of length (>= "+ str(maxlen)+ "%)"    
        definitions['SS']   = "Filtered because of non canonical junction (neither CT_AC nor GT_AG)"
        definitions['PASS'] = "Retained"
        
        global_stat_detected_introns = dict()
        global_stat_detected_introns["0Number"] = df_candidat.shape[0]
        global_stat_detected_introns["1Mean length"] = 0
        for i,row in df_candidat.iterrows():
            global_stat_detected_introns["1Mean length"] += row['end'] - row['start'] + 1
        global_stat_detected_introns["1Mean length"] /= (global_stat_detected_introns["0Number"])
        global_stat_detected_introns["1Mean length"] = round(global_stat_detected_introns["1Mean length"], 2)
        global_stat_detected_introns["2Mean depth"]= round(df_candidat['depth'].mean(), 2)

        # fonction html pour les détectés
        # # qui fera tableau et graph

        global_stat_filtred_detected_introns = dict()  ##TODO  filtred / filtered
        global_stat_filtred_detected_introns["0" + definitions['PASS']] = 0
        global_stat_filtred_detected_introns["1" + definitions['DP']]   = 0
        global_stat_filtred_detected_introns["2" + definitions['LEN']]  = 0
        global_stat_filtred_detected_introns["3" + definitions['SS']]   = 0
        
        for i, v in (df_candidat['filter'].items()) :
            if "PASS" in v:
                global_stat_filtred_detected_introns["0" + definitions['PASS']] += 1
            if "DP" in v:
                global_stat_filtred_detected_introns["1" + definitions['DP']]   += 1
            if "LEN" in v:
                global_stat_filtred_detected_introns["2" + definitions['LEN']]  += 1
            if "SS" in v:
                global_stat_filtred_detected_introns["3" + definitions['SS']]   += 1

        # fonction html pour les filtrés
        #html += get_html_detected(global_stat_filtred_detected_introns)   

     
        ###
        # TODO gestion rapport cadre simulation ou vraie vie
        # if ? simulation ?
        ###
        
        # Tableau features detectable
        # 1 nombre de features 
        # 2 nombre de features retenus
        # 3 .... nombre de features filtrées because of
        # Add a column to df_features with the DP (using df_library)
        df_features["DP"] = df_features.apply(
            compute_dp,
            axis = 1,
            df_library=df_library
        )
        
        # Add a column to df_features with the lenght of the corresponding contig (using df_fasta)
        df_features["ctg_length"] = df_features.apply(
            compute_len,
            axis = 1,
            df_fasta=df_fasta
        )

        global_stat_detectable_features = dict()
        global_stat_detectable_features["0Number of features"] = df_features.shape[0]
        global_stat_detectable_features["1" + definitions['PASS']] = 0
        global_stat_detectable_features["2" + definitions['DP']]   = 0
        global_stat_detectable_features["3" + definitions['LEN']]  = 0
        global_stat_detectable_features["4" + definitions['SS']]   = 0
        
        for index, row in df_features.iterrows():
            PASS = True
            if ('CT_AC' not in row['flanks'] or 'GT_AG' not in row['flanks']) :
                global_stat_detectable_features["4" + definitions['SS']] += 1
                PASS = False 
            if (((row['end'] - row['start'] + 1) / row['ctg_length']) >= int(maxlen)):
                global_stat_detectable_features["3" + definitions['LEN']] += 1
                PASS = False
            if (row['DP'] <= mindepth):
                global_stat_detectable_features["2" + definitions['DP']] += 1
                PASS = False
            if PASS:
               global_stat_detectable_features["1" + definitions['PASS']] += 1     
 
        html += get_html_detectable_features(global_stat_detectable_features)
        # fonction gethtml_detectablefeatures (dict detectablefeatures)

        # Comparison between candidats and features from GTF file
        nbTotCandidatsIncludingFeatures, nbSameStartEnd, nbLen, minimumDepth, nonCanonical=candidatsVsFeatures(df_candidat, df_features, mindepth, maxlen)

        # Comparison between candidats and features from GTF file
        global_stat_candidat_vs_gtf = dict()
        global_stat_candidat_vs_gtf["0Number of detected introns"] = global_stat_detected_introns["0Number"]
        c = 0
        for k, v in (df_features.feature.value_counts()).items() :
            global_stat_candidat_vs_gtf[str(c)+'Number of '+k+ ' in GTF'] = v
            c+=1
        # Add nb reads overlapping each feature in df_cov_lect
        detectableIntrons, TP, detectablePreditNeg, nbFeaturesWithoutReads, nbIntronsWithReadsBelowCov =  process_intron(df_features,df_library, df_candidat, meanCoverage)
        global_stat_candidat_vs_gtf[str(c+1)+"Number of introns with split reads"]                    = detectableIntrons
        global_stat_candidat_vs_gtf[str(c+2)+"Detected introns not found in GTF"]                     =  df_candidat.shape[0] - df_features.shape[0]
        global_stat_candidat_vs_gtf[str(c+3)+"Number of features without read"]                       = nbFeaturesWithoutReads
        
        
        global_stat_candidat_vs_features=dict()
        global_stat_candidat_vs_features["0Number of introns with reads below depth"]              = nbIntronsWithReadsBelowCov
        global_stat_candidat_vs_features["1Total number of candidats including features"]          = nbTotCandidatsIncludingFeatures
        global_stat_candidat_vs_features["2Number of features with same start end than candidats"] = nbSameStartEnd
        global_stat_candidat_vs_features["3Number of features length >="+str(maxlen)]              = nbLen
        global_stat_candidat_vs_features["4Number of features with depth <= "+str(mindepth)]       = minimumDepth
        global_stat_candidat_vs_features["5Number of features without canonical junctions"]        = nonCanonical

        html += get_html_candidat_descr(global_stat_detected_introns, global_stat_filtred_detected_introns, df_candidat)
        print("Detected introns statistics and histogram")
      
    # Precision, recall and F1 score
    #  TP is the number of detectable and found features (int value)
    #  TN is the number of detectable and not found features (int value)
    #  FP is the number of undetectable and found features (int value)
    #  FN is the number of undetectable and not found features (int value)    
    FP=nbPASS - TP                       #nbPASS = predits positives
    TN=42  #nbPASSdepLEN = predits negatives
    FN=42 #nbPASSdepLEN-TN


    global_stat_precision= dict()
    precision = TP/(FP+TP)
    global_stat_precision["0Precision (between 0 - 1)"]= precision
    recall = TP/(TN+TP)
    global_stat_precision["1Recall or sensitivity (0.0 for no recall, 1.0 for full or perfect recall)"] = recall
    global_stat_precision["2F1 score (1 for a perfect model, 0 for a failed model)"]  = 2*((precision*recall)/(precision+recall))

    html += get_html_precision(global_stat_precision, TP, TN, FP, FN, global_stat_candidat_vs_gtf, global_stat_candidat_vs_features, meanCoverage)
    print("Detectability statistics")

    # GLOSSARY
    html += get_html_glossary()

    # FOOTER
    html += "<br/>"
    html += get_html_footer()

    with open(output_file, "w") as f:
        f.write(html)

    print('DATAFRAMES:\n\n')
    print('fasta head :' , df_fasta.head(5), '\n\n')
    print('mfasta head :' , df_mfasta.head(5), '\n\n')
    print('library head :' , df_library.head(5), '\n\n')
    print('features head :', df_features.head(5), '\n\n')
    if split:
        print('df_split', df_split, '\n\n')
    if candidat:
        print('df_candidat', df_candidat, '\n\n')


if __name__ == '__main__' :
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--config_file')
    args, left_argv = parser.parse_known_args()
    if args.config_file:
        with open(args.config_file, 'r') as f:
            config = configparser.ConfigParser()
            config.read([args.config_file])
    
    parser = ArgumentParser()
    parser.add_argument('--config-file', type=argparse.FileType('r'), required=False, help="Provide a config file")
    parser.add_argument('-f','--fasta', type=argparse.FileType('r'), required=True, dest='fasta', help="Path to the reference FASTA file.")
    parser.add_argument('-m','--modified-fasta', type=argparse.FileType('r'), required=True, dest='mfasta', help="Path to the modified FASTA file.")
    parser.add_argument('-g','--gtf', type=argparse.FileType('r'), required=True, dest='gtf', help="GTF filename which contains the genome annotation.")
    parser.add_argument('-1','--R1', type=argparse.FileType('r'), required=True, dest='r1', help="Name of the  FASTQ  file  which  contains  the  single-end   reads library. If paired-end, filename of #1 reads mates")
    parser.add_argument('-2','--R2', type=argparse.FileType('r'), required=False, dest='r2', help="Only for a paired-end library, filename of #2 reads mates.")
    parser.add_argument('--flagstat', type=argparse.FileType('r'), required=False, dest='flagstat', help="Path to flagstat file.")
    parser.add_argument('-r','--ranks', type=argparse.FileType('r'), required=False, dest='ranks', help="Path to ranks file.")
    parser.add_argument('-c','--candidat', type=argparse.FileType('r'), required=False, dest='candidat', help="Path to candidat file.")
    parser.add_argument('-s','--split', type=argparse.FileType('r'), required=False, dest='split', help="Path to split file.")
    parser.add_argument('-o','--output', type=str, required=True, dest='output', help="Output dir name.")
    parser.add_argument('-p', '--prefix', type=str, required=False, default="", dest='prefix', help="Prefix for output files name.")
    parser.add_argument('-t','--threads', type=int, default=1, required=False, dest='threads', help="Number of threads [1]")
    parser.add_argument('-F', '--force', action='store_true', default=False, dest='force', help="Force to overwrite output files.")

    try:
        config
    except NameError:
        pass
    else:
        for k, v in config.items("Defaults"):
            config_args={str(k): str(v)} 
            # https://stackoverflow.com/questions/47892580/python-argparse-required-arguments-from-configuration-file-dict
            # use values from configuration file by default
            parser.set_defaults(**config_args)
            # Reset `required` attribute when provided from config file
            for action in parser._actions:
                if action.dest in config_args:
                    action.required = False

    # override with command line arguments when provided
    args = vars(parser.parse_args(left_argv, args))

    print(args)

    simulationReport(**args)
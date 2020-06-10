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

# config = configparser.RawConfigParser() # On créé un nouvel objet "config"
# config.read('parameters') # On lit le fichier de paramètres
# # Récupération des parametres dans des variables
# fasta        = config.get('MANDATORY','fasta')
# mfasta       = config.get('MANDATORY','mfasta')
# gtf          = config.get('MANDATORY','gtf')
# r1           = config.get('MANDATORY','R1')
# output       = config.get('MANDATORY','output')
# threads      = config.get('MANDATORY','t')
# r2           = config.get('OPTIONNAL','R2')
# flagstat     = config.get('OPTIONNAL','flagstat')
# ranks        = config.get('OPTIONNAL','ranks')
# candidat     = config.get('OPTIONNAL','candidat')
# split        = config.get('OPTIONNAL','split')
# prefix       = config.get('OPTIONNAL','prefix')
# force        = config.get('OPTIONNAL','force')

# source activate ISeeker_environment;
# cd scripts/; 
# python3 simulation2HTML.py --config_file parameters.config -f /home/Sarah/Documents/PROJETS/INTRONSEEKER/FRS/CAS-A/sample1/frs_sample1_contigs.fa -F -p "FRS_CASA_sample1_n1000_r_STAR"
# scp  /home/Sarah/Documents/PROJETS/INTRONSEEKER/FRS/CAS-A/sample1/HTML/*.html smaman@genologin.toulouse.inra.fr:/save/smaman/public_html/intronSeeker/.
# See result : http://genoweb.toulouse.inra.fr/~smaman/intronSeeker/report_FRS_CASA_sample1_n1000_r_STAR_simulation.html

############
# SUB MAIN #
############
def simulationReport(   config_file: str,fasta:str, mfasta:str, gtf:str, r1:str, r2:str, ranks:str,
                        flagstat:str, candidat:str, split:str,
                        output:str, prefix:str, force:bool, threads:int ) :
    
    #Return the value (in fractional seconds) of the sum of the system and user CPU time of the current process. 
    #It does not include time elapsed during sleep. 
    #It is process-wide by definition. 
    #The reference point of the returned value is undefined, 
    #so that only the difference between the results of consecutive calls is valid.
    tmps1=time.process_time()
    
    #Return the value (in fractional seconds) of a performance counter
    #Only the difference between the results of consecutive calls is valid.
    tmps1c=time.perf_counter() 

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
    print("CPU time = %f" %(time.process_time()-tmps1))
    print("Performance counter = %f\n" %(time.perf_counter()-tmps1c))
    tmps2=time.process_time()
    tmps2c=time.perf_counter() 

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
    candidat_file=""    
    if candidat:
        candidat_file=candidat.name
        inputfiles.append("Candidat#" + os.path.basename(candidat.name))

    html += get_html_body1(flagstat_file, candidat_file)

   
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

    # Assemblathon on fasta files
            
    nbContigs, totContigSize, longestContig, shortestContig, nbContigsSup1K, n50, l50, meanContigSize = assemblathon_stats(fasta.name)
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
        nbContigs, totContigSize, longestContig, shortestContig, nbContigsSup1K, n50, l50, meanContigSize = assemblathon_stats(mfasta.name)
        global_stat_assemblathon_mfasta = dict()
        global_stat_assemblathon_mfasta["0Number of contigs"]         = nbContigs
        global_stat_assemblathon_mfasta["1Mean contigs length"]       = round(meanContigSize, 0)
        global_stat_assemblathon_mfasta["2Total size of contigs"]     = totContigSize
        global_stat_assemblathon_mfasta["3Longest contig"]            = longestContig
        global_stat_assemblathon_mfasta["4Shortest contiged"]         = shortestContig
        global_stat_assemblathon_mfasta["5Number of contigs > 1K nt"] = nbContigsSup1K
        global_stat_assemblathon_mfasta["6N50 contig length"]         = n50
        global_stat_assemblathon_mfasta["7L50 contig count"]          = l50

    # if mfasta:
    #     assemblathon_mfasta_name = output_path + "_" + os.path.splitext(os.path.basename(mfasta.name))[0] + '_assemblathon.txt'
    #     with open(assemblathon_mfasta_name,'w') as assemblathon_mfasta :
    #         sp.run(['/home/Sarah/Documents/PROJETS/INTRONSEEKER/DATATEST/intronSeeker/bin/assemblathon_stats.pl',mfasta.name],stdout=assemblathon_mfasta)   
    #         df_assemblathon_mfasta = parse_assemblathon(assemblathon_mfasta, "title")
    #         global_stat_assemblathon_mfasta = dict()
    #         global_stat_assemblathon_mfasta["0Number of contigs"]         = df_assemblathon_mfasta.iloc[0,0]
    #         global_stat_assemblathon_mfasta["1Mean contigs length"]       = int(df_assemblathon_mfasta.iloc[1,0]) / int(df_assemblathon_mfasta.iloc[0,0])
    #         global_stat_assemblathon_mfasta["2Total size of contigs"]     = df_assemblathon_mfasta.iloc[1,0]
    #         global_stat_assemblathon_mfasta["3Longest contig"]            = df_assemblathon_mfasta.iloc[2,0]
    #         global_stat_assemblathon_mfasta["4Shortest contiged"]         = df_assemblathon_mfasta.iloc[3,0]
    #         nbLongContigs=re.sub(r'([a-zA-Z0-9_]*.[a-zA-Z0-9_]*%)', r" ", df_assemblathon_mfasta.iloc[4,0])
    #         global_stat_assemblathon_mfasta["5Number of contigs > 1K nt"] = nbLongContigs
    #         global_stat_assemblathon_mfasta["6N50 contig length"]         = df_assemblathon_mfasta.iloc[5,0]
    #         global_stat_assemblathon_mfasta["7L50 contig count"]          = df_assemblathon_mfasta.iloc[6,0]

    print("Global statistics")
    print("CPU time = %f" %(time.process_time()-tmps2))
    print("Performance counter = %f\n" %(time.perf_counter()-tmps2c))
    tmps3=time.process_time()
    tmps3c=time.perf_counter() 


    html += get_html_seq_descr(global_stat, nb_ctg_by_feature, ctg_descr, gtf.name, df_features['pos_on_contig'], df_fasta, df_mfasta, global_stat_assemblathon_fasta, global_stat_assemblathon_mfasta)


    # READS STAT
    # Global stat
    global_stat_fastq = dict()
    global_stat_fastq["0Number of reads"] = df_library['contig'].count()
    global_stat_fastq["1Mean coverage"] = 0
    for i,row in df_library.iterrows():
        global_stat_fastq["1Mean coverage"] += row['end'] - row['start'] + 1
    global_stat_fastq["1Mean coverage"] /= (global_stat["1Contig FASTA - Mean seq. length"] * global_stat["0Contig FASTA - Number of seq."])
    global_stat_fastq["1Mean coverage"] = round(global_stat_fastq["1Mean coverage"], 2)
    global_stat_fastq["2Min reads length"] = df_features['length'].min()
    global_stat_fastq["3Max reads length"] = df_features['length'].max()
    global_stat_fastq["4Mean reads length"] = round(df_features['length'].mean())
      
    html += get_html_reads_descr(global_stat_fastq)
    print("Reads statistics")
    print("CPU time = %f" %(time.process_time()-tmps3))
    print("Performance counter = %f\n" %(time.perf_counter()-tmps3c))
    tmps4=time.process_time()
    tmps4c=time.perf_counter() 


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
    html += get_html_abundance(df_fasta)
    print("Abundance")
    print("CPU time = %f" %(time.process_time()-tmps4))
    print("Performance counter = %f\n" %(time.perf_counter()-tmps4c))
    tmps5=time.process_time()
    tmps5c=time.perf_counter() 

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
    print("CPU time = %f" %(time.process_time()-tmps5))
    print("Performance counter = %f\n" %(time.perf_counter()-tmps5c))
    tmps6=time.process_time()
    tmps6c=time.perf_counter() 


    ## SPLITREADSEARCH STAT
    if split:
        df_split=parse_split(split.name)   
        global_stat_split = dict()
        global_stat_split["0Number of reads overlapping potential retained introns"]= df_split.shape[0]
        global_stat_split["1Mean length of potential retained introns"]= df_split['split_length'].mean()

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
    print("CPU time = %f" %(time.process_time()-tmps6))
    print("Performance counter = %f\n" %(time.perf_counter()-tmps6c))
    tmps7=time.process_time()
    tmps7c=time.perf_counter() 


    # Candidat statistics - detected introns
    if candidat:
        df_candidat, mindepth, maxlen = parse_candidat(candidat.name)

         # Definition dict
        definitions = dict()
        definitions['DP']   = "Number of detected introns depth <= min depth ("+ str(mindepth) +")"
        definitions['LEN']  = "Number of detected introns length >= max len ("+ str(maxlen) +")"
        definitions['SS']   = "Number of features without canonical borders (neither CT_AC nor GT_AG)"
        definitions['PASS'] = "Number of features with canonical borders (CT_AC or GT_AG) and ...."
        
        global_stat_detected_introns = dict()
        global_stat_detected_introns["0Number"] = df_candidat.shape[0]
        global_stat_detected_introns["1Mean length"] = 0
        for i,row in df_candidat.iterrows():
            global_stat_detected_introns["1Mean length"] += row['end'] - row['start'] + 1
        global_stat_detected_introns["1Mean length"] /= (global_stat_detected_introns["0Number"])
        global_stat_detected_introns["1Mean length"] = round(global_stat_detected_introns["1Mean length"], 2)
        global_stat_detected_introns["2Mean depth"]= round(df_candidat['depth'].mean(), 2)


        global_stat_filtred_detected_introns = dict()
        c = 0
        for k, v in (df_candidat['filter'].value_counts()).items() :
            for key, value in definitions.items():
                if k == key:
                    global_stat_filtred_detected_introns[str(c)+k+" ("+value+")"] = v
                    c+=1


        # Comparison between candidats and features from GTF file
        nbTotCandidatsIncludingFeatures, nbSameStartEnd, nbLen, minimumDepth, nonCanonical=candidatsVsFeatures(df_candidat, df_features, mindepth, maxlen)

        global_stat_candidat_vs_gtf = dict()
        global_stat_candidat_vs_gtf["0Number of detected introns"] = global_stat_detected_introns["0Number"]
        c = 1
        for k, v in (df_features.feature.value_counts()).items() :
            global_stat_candidat_vs_gtf[str(c)+'Number of '+k+ ' in GTF'] = v
            c+=1
        global_stat_candidat_vs_gtf[str(c+1)+"Number of detected introns corresponding features (Overlaps)"] = nbSameStartEnd
        global_stat_candidat_vs_gtf[str(c+2)+"Detected introns not found in GTF"]   = global_stat_detected_introns["0Number"]- nbTotCandidatsIncludingFeatures
        

        html += get_html_candidat_descr(global_stat_detected_introns, global_stat_filtred_detected_introns, df_candidat)
        print("Detected introns statistics and histogram")
    print("CPU time = %f" %(time.process_time()-tmps7))
    print("Performance counter = %f\n" %(time.perf_counter()-tmps7c))
    tmps8=time.process_time()
    tmps8c=time.perf_counter() 


    
    # df_cov_lect =  process_intron(df_features,df_library)
    # print('df_cov_lect', df_cov_lect)
    
    # Precision, recall and F1 score
    # TP is the number of detectable and found features (int value)
    # TN is the number of detectable and not found features (int value)
    # FP is the number of undetectable and found features (int value)
    # FN is the number of undetectable and not found features (int value)
    
    # https://fr.wikipedia.org/wiki/Pr%C3%A9cision_et_rappel"
    ##  les "features" qui ont assez de lectures les couvrant pour être trouvées. Il n'y que celles-ci qui pourront être vues comme T (True).
    # TP = nombre de "features" détectables et trouvées (assez de profondeur et bonnes bornes). 
    #TP = nbTotCandidatsIncludingFeatures
    TP = 42
    # TN = nombre de "features" détectables non couvertes par des lectures et/ou couvertes par un nombre de lectures après alignement sont sous le seuil de profondeur (alors que dans la simulation c'était le cas)
    # PROFONDEUR (DEP)
    #TN =  minimumDepth
    TN = 42
    # FP = nombre de zones hors "feature" ou "features" indétectables avec une couverture insuffisante
    # COUVERTURE (LEN)
    #FP = nbSameStartEnd
    FP = 42
    # FN = nombre de zones hors "feature" ou "features" indétectables trouvées (passant le seuil de profondeur)
    # df_candidat.shape[0] - df_features.shape[0]
    FN = 42

    # global_stat_precision= dict()
    # precision = TP/(FP+TP)
    # global_stat_precision["0Precision (between 0 - 1)"]= precision
    # recall = TP/(TN+TP)
    # global_stat_precision["1Recall or sensitivity (0.0 for no recall, 1.0 for full or perfect recall)"] = recall
    # #global_stat_precision["2F1 score (1 for a perfect model, 0 for a failed model)"]  = 2*((global_stat_precision["0Precision"]*global_stat_precision["1Recall"])/(global_stat_precision["0Precision"]+global_stat_precision["1Recall"]))
    # global_stat_precision["2F1 score (1 for a perfect model, 0 for a failed model)"]  = 2*((precision*recall)/(precision+recall))

    # html += get_html_precision(global_stat_precision, TP, TN, FP, FN, global_stat_candidat_vs_gtf)

    print("Detectability statistics")
    print("CPU time = %f" %(time.process_time()-tmps8))
    print("Performance counter = %f\n" %(time.perf_counter()-tmps8c))
    tmps9=time.process_time()
    tmps9c=time.perf_counter() 

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
    parser.add_argument('--config_file', help='config file')
    args, left_argv = parser.parse_known_args()
    if args.config_file:
        with open(args.config_file, 'r') as f:
            config = configparser.ConfigParser()
            config.read([args.config_file])
    
    parser = ArgumentParser()
    parser.add_argument('-f','--fasta', type=argparse.FileType('r'), required=False, dest='fasta')
    parser.add_argument('-m','--modifiedfasta', type=argparse.FileType('r'), required=False, dest='mfasta')
    parser.add_argument('-g','--gtf', type=argparse.FileType('r'), required=False, dest='gtf')
    parser.add_argument('-1','--R1', type=argparse.FileType('r'), required=False, dest='r1')
    parser.add_argument('-2','--R2', type=argparse.FileType('r'), required=False, dest='r2')
    parser.add_argument('--flagstat', type=argparse.FileType('r'), required=False, dest='flagstat')
    parser.add_argument('-r','--ranksfile', type=argparse.FileType('r'), required=False, dest='ranks')
    parser.add_argument('-c','--candidat', type=argparse.FileType('r'), required=False, dest='candidat')
    parser.add_argument('-s','--split', type=argparse.FileType('r'), required=False, dest='split')
    parser.add_argument('-o','--output', type=str, required=False, dest='output')
    parser.add_argument('-p', '--prefix', type=str, required=False, default="", dest='prefix')
    parser.add_argument('-t','--threads', type=int, default=1, required=False, dest='threads')
    parser.add_argument('-F', '--force', action='store_true', default=False, dest='force')


    n=0
    for k, v in config.items("Defaults"):
        #parser.parse_args([str(k), str(v)], args)
        config_args={str(k): str(v)} 
        # https://stackoverflow.com/questions/47892580/python-argparse-required-arguments-from-configuration-file-dict
        # use values from configuration file by default
        parser.set_defaults(**config_args)
        # Reset `required` attribute when provided from config file
        for action in parser._actions:
            if action.dest in config_args:
                action.required = False
        print('REQUIRED config_args : ',config_args)
        n += 1

    if n < 6:   
        print('6 required arguments are mandatory')
        exit(1)    

    for k, v in config.items("Optionnal"):
        #parser.parse_args([str(k), str(v)], args)
        config_args={str(k): str(v)} 
        parser.set_defaults(**config_args)
        print('OPTIONNAL config_args : ',config_args)     

    # override with command line arguments when provided
    args = vars(parser.parse_args(left_argv, args))

    print(args)

    simulationReport(**args)
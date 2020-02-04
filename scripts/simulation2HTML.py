#!/usr/bin/env python3

import os
import configparser
import numpy as np
import pandas as pd
import plotly as py
import plotly.graph_objects as go



import re
import pickle
import pysam
import gzip
import time
import sys
import concurrent.futures as prl
import tempfile
#import matplotlib.pyplot as plt
#from scipy.stats import gaussian_kde
from IPython.display import HTML
from pprint import pprint
from collections import OrderedDict
from itertools import repeat
from Bio import SeqIO
from intronSeekerPlot import *

#https://stackoverflow.com/questions/9252543/importerror-cannot-import-name-x
#  File "/home/sigenae/.conda/envs/ISeeker_environment/lib/python3.6/site-packages/charts/__init__.py", line 5, in <module>
#    from plot import plot, plotasync, line, area, spline, pie
#ImportError: cannot import name 'plot'  --> le package charts n ait pas bouge depuis 2015 ... et que les problèmes d'incompatibilité avec Python3 perdurent ...
#DONC choix d'un package plus actuel.
#https://github.com/kyper-data/python-highcharts/blob/master/examples/highcharts/Example1.py


#step 1  full random simulation : intronSeeker fullRandomSimulation -r -o FRS/ 
#$ conda deactivate
#test : module load system/Python-3.7.4;
#module load system/Miniconda3-4.7.10;
#source activate ISeeker_environment;
#cd scripts/; 
#python3 simulation2HTML.py -g ../FRS/frs_modifications.gtf -r ../FRS/frs_contigs-modified.fa -f ../FRS/frs_contigs.fa -o HTML
#python3 simulation2HTML.py -g /work/project/sigenae/sarah/intronSeeker/FRS/CAS-A/sample1/frs_sample1_modifications.gtf -r /work/project/sigenae/sarah/intronSeeker/FRS/CAS-A/sample1/frs_sample1_contigs-modified.fa -f /work/project/sigenae/sarah/intronSeeker/FRS/CAS-A/sample1/frs_sample1_contigs.fa -o HTML/
#simulate reads : config/grinder_frs_testA.cfg

def plot_gtf(gtf_file):
    #Tableau 1 - https://plot.ly/python/table/
    #df = pd.read_fwf(gtf_file, sep = "\t")
    df = pd.read_table(gtf_file, sep='\t', header = None, names = ['contig', 'frs', 'intron', 'start', 'end', 'x1', 'x2', 'x3', 'x4'])

    summary_table_1 = go.Figure(data=[go.Table(
    header=dict(values=list(df.columns),
                fill_color='paleturquoise',
                align='left'),
    cells=dict(values=[df.contig, df.frs, df.intron, df.start, df.end, df.x1, df.x2, df.x3, df.x4],
               fill_color='lavender',
               align='left'))
    ])
    #summary_table_1.show()
    #Mise en forme du tableau
    summary_table_1 = df.describe()
    #summary_table_1 = summary_table_1.to_html()
    return summary_table_1 
   
   
#Distribution des tailles d introns
def parse_length_introns(gtf_file) :
    table = pd.read_table(gtf_file, sep='\t', header = 0, names = ['contig', 'frs', 'intron', 'start', 'end', 'x1', 'x2', 'x3', 'x4'])
    table["length"] = table["end"]-table["start"]
    return table.set_index('length')

#http://www.xavierdupre.fr/app/teachpyx/helpsphinx/i_ex.html
def parse_nb_introns_by_contig(gtf_file) :
    table = pd.read_table(gtf_file, sep='\t', header = None, names = ['contig', 'frs', 'intron', 'start', 'end', 'x1', 'x2', 'x3', 'x4'])
    l=table["contig"]
    d = {}
    for x in l:
        d[x] = d.get(x, 0) + 1
    return d



def general_stats_on_contig(modifiedfa_file, gtf_file):
    #files and paths
    figFiles = go.Figure(data=[go.Table(header=dict(values=['data', 'File name/path']),
                cells=dict(values=[['FRS'], [gtf_file, fa_file, modifiedfa_file]]))
                    ])
    #figFiles.show()               
    #figFiles.to_html()
    
    #Stats
    fig = go.Figure(data=[go.Table(header=dict(values=['Nb contigs/transcripts', 'Nb contigs/transcripts with introns', 'Nb introns']),
                cells=dict(values=[[nContigsAvecIntrons], [ nContigsAvecIntrons-nContigs], [nIntrons]]))
                    ])
    #fig.show()
    #Mise en forme du tableau
    #fig = fig.to_html()
   





# Return int
def count_seq_from_fa(fasta):
    nb_seq = 0;
    for line in open(fasta):
        if line.startswith('>'):
            nb_seq += 1
    return nb_seq

# Return dict : item_name => int
def count_items_from_gtf(gtf):
    nb_items = dict();
    for line in open(gtf):
        if not line.startswith('#'):
            nb_items[line.split()[2]] = nb_items.get(line.split()[2], 0) + 1
    return nb_items

# Return ?
def t(gtf):
    ctg_descr = dict()
    for line in open(gtf):
        if not line.startswith('#'):
            k = line.split()[0]
            if k in ctg_descr:
                ctg_descr[k][line.split()[2]] = ctg_descr[k].get(line.split()[2], 0) + 1
            else:
                ctg_descr[k] = dict()
                ctg_descr[k][line.split()[2]] = ctg_descr[k].get(line.split()[2], 0) + 1
    
    res = []
    for ctg in ctg_descr.values():
        tmpstr = ""
        for key1, value1 in sorted(ctg.items(), key=lambda t: t[0]):
            tmpstr += str(key1)+"#"+str(value1)+"\n"
        res.append(tmpstr)
    unique_elements, counts_elements = np.unique(res, return_counts=True)
    print(np.asarray((unique_elements, counts_elements)))
    return

def simulationReport(modifiedfa : str, gtf : str, output : str, prefix : str) :
    output_path = output + "/html";
    if prefix:
        output_path += "_" + prefix;
    
    # Create output dir if not exist
    if not os.path.exists(output) :
        os.mkdir(output)
    
    t(gtf.name)
    return
    
    #create the report in a HTML file
    figtable=fig\
        .to_html()\
        .replace('<table border="1" class="dataframe">','<table class="table table-striped">') # use bootstrap styl
    
    figFilestable=figFiles\
        .to_html()\
        .replace('<table border="1" class="dataframe">','<table class="table table-striped">') # use bootstrap styl
    
    lengthDistrib=parse_length_introns(gtf.name)
    lengthDistribTable=lengthDistrib\
        .to_html()\
        .replace('<table border="1" class="dataframe">','<table class="table table-striped">') # use bootstrap styl
            
    #introns_length_plot_url = py.plot(lengthDistrib, filename='Introns length', auto_open=False,)
    #filesList_plot_url = py.plot(figFiles, height=1000, width=1000, auto_open=False,\
    #                      filename='Major technology and CPG stock prices in 2014 - scatter matrix')
    #<h3>Files list: """ + filesList_plot_url + """</h3>
	#<h3>Introns lengths: """ + introns_length_plot_url + """</h3>

    reportFile = '%s/%s' % (output,'stats.html')
    
    #http://www.xavierdupre.fr/app/ensae_teaching_cs/helpsphinx/notebooks/td1a_cenonce_session_10.html
    print ('length line 1', lengthDistrib.head(1))
    #print ('length contig', lengthDistrib.loc["length"])
    
    IntronsByContig = Highchart()
    IntronsByContig.add_data_set(nbIntronsByContig, series_type='line', name='Example Series')
    IntronsByContig.save_file(reportFile)
    
    
    
	
    with open(reportFile,"a+") as f:
       contenu ="""
	   <html>
      <head>
	   <link rel="stylesheet" href="/work/project/sigenae/sarah/intronSeeker/scripts/bootstrap.min.css">
	   <style>body{ margin:0 100; background:whitesmoke; }</style>
	   </head>
	   <body>
	   <h1>FRS - STAR / HISAT2 comparison</h1>
	   <h3>Files list and paths:  """ + figFilestable + """ </h3>
	   <h3>Introns / Contigs / Transcripts: """ + figtable + """</h3>
	   <h3>Introns lengths distribution: """ + lengthDistribTable + """</h3>
       </body>
       </html>"""
       f.write(contenu)
       f.close() 
    
    pass
#plots : https://python-graph-gallery.com/

if __name__ == '__main__' :
    
    import argparse 
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-f','--fasta', type=argparse.FileType('r'), required=True, dest='modifiedfa')
    parser.add_argument('-g','--gtf', type=argparse.FileType('r'), required=True, dest='gtf') 
    parser.add_argument('-o','--output', type=str, required=True, dest='output')
    parser.add_argument('-p', '--prefix', type=str, required=False, default="", dest='prefix')

    args = vars(parser.parse_args())
    
    simulationReport(**args)
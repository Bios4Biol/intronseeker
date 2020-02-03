#!/usr/bin/env python3

import re
import pickle
import os
import pandas as pd
import pysam
import gzip
import time
import sys
import numpy as np
import plotly as py
#import plotly.plotly as py
#import plotly.tools as plotly_tools
#import plotly.graph_objs as go
import configparser
import concurrent.futures as prl
import tempfile
os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()
#import matplotlib.pyplot as plt
#from scipy.stats import gaussian_kde
from IPython.display import HTML
from pprint import pprint
from collections import OrderedDict
from itertools import repeat
from Bio import SeqIO
from intronSeekerPlot import *
from highcharts import Highchart # import highchart library
#ModuleNotFoundError: No module named 'highcharts'
#(ISeeker_environment) sigenae@genologin2 /work/project/sigenae/sarah/intronSeeker/scripts $ pip install python-highcharts
#https://github.com/kyper-data/python-highcharts
from json import JSONEncoder
import json

#The plotly.plotly module is deprecated,
#please install the chart-studio package and use the
#chart_studio.plotly module instead. 


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
#Tests 
#../../IntronSeeker_1rst_tests/Tests_Janv2020/intronSeeker/FRS/
#simulationReport.py --R1 ../../IntronSeeker_1rst_tests/Tests_Janv2020/intronSeeker/FRS/sr_test1_R1.fastq.gz --R2 ../../IntronSeeker_1rst_tests/Tests_Janv2020/intronSeeker/FRS/sr_test1_R2.fastq.gz --reference ../../IntronSeeker_1rst_tests/Tests_Janv2020/intronSeeker/FRS/frs_test1_contigs.fa --alignment ../../IntronSeeker_1rst_tests/Tests_Janv2020/intronSeeker/FRS/hisat2_test1.sort.bam --split-alignments ../../IntronSeeker_1rst_tests/Tests_Janv2020/intronSeeker/FRS/srs_test1_split_alignments.txt  --frs ???? TODO 
    
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
    #add a column length
    table['LENGTH_calculated'] = table["length"]
    #return table.set_index('length')
    return table

#http://www.xavierdupre.fr/app/teachpyx/helpsphinx/i_ex.html
def parse_nb_introns_by_contig(gtf_file) :
    table = pd.read_table(gtf_file, sep='\t', header = None, names = ['contig', 'frs', 'intron', 'start', 'end', 'x1', 'x2', 'x3', 'x4'])
    l=table["contig"]
    d = {}
    for x in l:
        d[x] = d.get(x, 0) + 1
    return d
    
def stats_contigs_introns(fa_file, modifiedfa_file, gtf_file):
    for line in open(fa_file):
        if line.startswith('>'):
            nContigs = sum(1 for _ in open(fa_file))
            nContigsAvecIntrons = sum(1 for _ in open(modifiedfa_file))
    
    nIntrons = sum(1 for _ in open(gtf_file))
     
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
    
    #Nombre min / max / moyen d'introns retenus par contig
    nbIntronsByContig=parse_nb_introns_by_contig(gtf_file)
    print ('Nb introns par contig: ', nbIntronsByContig)
    #charts.plot(nbIntronsByContig, name='Second list data', show='inline', options=dict(title=dict(text='My second chart!')))
    #charts.html()

    return nIntrons, nContigsAvecIntrons, nContigs, nbIntronsByContig, fig, figFiles;
#https://www.geeksforgeeks.org/g-fact-41-multiple-return-values-in-python/
   
def barChart(gtf_file):

    lengthDistrib=parse_length_introns(gtf_file)
    print ('Intron lenght : ', lengthDistrib["LENGTH_calculated"])
    print ('contig: ', lengthDistrib["contig"])
    
    #encoder les series en JSON (Object of type 'Series' is not JSON serializable)
    #https://ncrocfer.github.io/posts/serialiser-une-instance-de-classe-en-json-sous-python/
    #class MyEncoder(json.JSONEncoder):
    #    def default(self, obj):
    #        if isinstance(obj, lengthDistrib):
    #            return vars(obj)
    #        else:
    #            return json.JSONEncoder.default(self, obj)
    #json.dumps(obj, cls=MyEncoder)

    #https://www.w3schools.com/python/python_json.asp
    contigname=json.dumps(lengthDistrib["contig"])
    contiglength=json.dumps(lengthDistrib["LENGTH_calculated"])
   
    distrib = Highchart(width=750, height=600)
    options = {
	'title': {
        'text': 'Stacked bar chart'
    },
    'subtitle': {
        'text': 'Source: Tests FRS'
    },
    'xAxis': {
        'categories': contigname,
        'title': {
            'text': None
        }
    },
    'yAxis': {
        'min': 0,
        'title': {
            'text': 'Population (millions)',
            'align': 'high'
        },
        'labels': {
            'overflow': 'justify'
        }
    },
    'tooltip': {
        'valueSuffix': ' millions'
    },
    'legend': {
        'layout': 'vertical',
        'align': 'right',
        'verticalAlign': 'top',
        'x': -40,
        'y': 80,
        'floating': True,
        'borderWidth': 1,
        'backgroundColor': "((Highcharts.theme && Highcharts.theme.legendBackgroundColor) || '#FFFFFF')",
        'shadow': True
    },
    'credits': {
        'enabled': False
    },
    'plotOptions': {
        'bar': {
            'dataLabels': {
                'enabled': True
            }
        }
    }
}
 
    pass
    
    
def chartIntronByContig(gtf_file):
    nbIntronsByContig=parse_nb_introns_by_contig(gtf_file)
    IntronsByContig = Highchart()
    IntronsByContig.add_data_set(nbIntronsByContig, series_type='line', name='Example Series')
    IntronsByContig.save_file(reportFile)
    
    pass
   
def simulationReport(fa : str, modifiedfa : str, gtf : str, output : str, prefix : str) :
    output_path = output + "/html";
    if prefix:
        output_path += "_" + prefix;
    
    # Create output dir if not exist
    if not os.path.exists(output) :
        os.mkdir(output)

    stats_contigs_introns(fa.name, modifiedfa.name, gtf.name)
       
    nIntrons, nContigsAvecIntrons, nContigs, nbIntronsByContig, fig, figFiles = stats_contigs_introns(fa.name, modifiedfa.name, gtf.name)
    
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
            

    reportFile = '%s/%s' % (output,'stats.html')
	
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
       
    chartIntronByContig(gtf.name)
    barChart(gtf.name)
    
    
    pass
#plots : https://python-graph-gallery.com/

if __name__ == '__main__' :
    
    import argparse 
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-f','--fasta', type=argparse.FileType('r'), required=True, dest='fa')
    parser.add_argument('-r','--reference', type=argparse.FileType('r'), required=True, dest='modifiedfa')
    parser.add_argument('-g','--gtf', type=argparse.FileType('r'), required=True, dest='gtf') 
    parser.add_argument('-o','--output', type=str, required=False, dest='output')
    parser.add_argument('-p', '--prefix', type=str, required=False, default="", dest='prefix')


    args = vars(parser.parse_args())
    
    simulationReport(**args)

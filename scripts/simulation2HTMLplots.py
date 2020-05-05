#!/usr/bin/env python3

import pandas as pd
import plotly as py
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.subplots as psp
from plotly.subplots import make_subplots   #for flagstat pie
import re   #for flagstat pie
import plotly.express as px #sunburst-charts

# Histogram   https://plotly.com/python/v3/histograms/
def plot_hist_contigs_len(fastaContigsLen, mFastaContigsLen):
    contigs = go.Histogram(
        x=fastaContigsLen,
        name='Contigs',
        opacity=0.75
    )
    modifiedContigs = go.Histogram(
        x=mFastaContigsLen,
        name='Modified contigs',
        opacity=0.75
    )
    data = [contigs, modifiedContigs]
    layout = go.Layout(
        xaxis=dict(
            title='Contigs length'
        ),
        yaxis=dict(
            title='Number of contigs'
        ),
        bargap=0.2,
        bargroupgap=0.1
    )
    fig = go.Figure(data=data, layout=layout)
    fig.update_layout(
        margin=go.layout.Margin(
            l=50,
            r=50,
            b=20,
            t=30,
            pad=0
        )
    )
    return py.offline.plot(fig, include_plotlyjs=False, output_type='div')



def plot_hist_candidats_depth(candidatsDepth):
    candidats = go.Histogram(
        x=candidatsDepth,
        name='Candidats',
        opacity=0.85
    )
    data = [candidats]
    layout = go.Layout(
         xaxis=dict(
            title='Candidats depth'
        ),
        yaxis=dict(
            title='Number of candidats'
        )
    )
    fig = go.Figure(data=data, layout=layout)
    fig.update_layout(
        margin=go.layout.Margin(
            l=50,
            r=50,
            b=20,
            t=30,
            pad=0
        )
    )   
    return py.offline.plot(fig, include_plotlyjs=False, output_type='div')


# Distribution plot
def plot_dist_features_len(len_by_features, feature_names):
    hist_data = len_by_features
    group_labels = feature_names
    colors = ['#333F44', '#37AA9C', '#94F3E4']
    # Create distplot with curve_type set to 'normal'
    fig = ff.create_distplot(hist_data, group_labels, show_hist=False, show_rug=True, colors=colors)
    fig.update_layout(
        xaxis=dict(
            title='Features length'
        ),
        margin=go.layout.Margin(
            l=50,
            r=50,
            b=20,
            t=30,
            pad=0
        )
    )
    return py.offline.plot(fig, include_plotlyjs=False, output_type='div')


# Plot introns position on a contigs
def plot_insertion_in_contig(positions) :
    hist = go.Histogram(
            x=positions,
            xbins=dict(
                start=0,
                end=100,
                size=2)#,
            #marker=dict(
            #    color='purple'
            #)
    )
    layout = go.Layout(xaxis=dict(title="% of contig length"),
                       yaxis=dict(title="Number of introns"))
    fig = go.Figure(data=[hist],layout=layout)
    fig.update_layout(
        margin=go.layout.Margin(
            l=50,
            r=50,
            b=20,
            t=30,
            pad=0
        )
    )
    return py.offline.plot(fig, include_plotlyjs=False, output_type='div')

# Plot ranks file
def plot_abondance_model(df_fasta:dict) :
    fig = go.Figure()
    if 'waiting' in df_fasta.columns:
        fig.add_trace(
            go.Scatter(
                x = df_fasta.index,
                y = df_fasta['waiting'],
                mode = 'lines',
                name ='Waited abundance'
            )
        )
    fig.add_trace(
        go.Scatter(
            x = df_fasta.index,
            y = df_fasta['real'],
            mode = 'lines',
            name = 'Abundance'
        )
    )
    fig.add_trace(
        go.Scatter(
            x = df_fasta.index,                              
            y = df_fasta['norm'],
            mode = 'lines',
            name = 'Normalized abundance'
        )
    )
    fig.update_layout(
        xaxis=dict(title="Contig names"),
        yaxis=dict(title="Abundance percentage",
        range=[-0.25,0.5]),
        margin=go.layout.Margin(
            l=50,
            r=50,
            b=20,
            t=30,
            pad=0
        )
    )
    return py.offline.plot(fig, include_plotlyjs=False, output_type='div')

# Plot : Counting table and barplots of mapped covering reads' main characteristics.
#def plot_covering_reads(*args, **kwargs) :
def plot_covering_reads(alignments:dict) :
    series=[]
    fig = go.Figure()
    for val in alignments:
        s = pd.Series()
        #{'query_name': '97482/2', 'reference_name': 'SEQUENCE103.modif', 'reference_start': 817, 'reference_end': 918, 'cigartuples': [(0, 101)], 'is_secondary': False, 'is_supplementary': False, 'mapping_quality': 60}
        s['Covering']=len(val)
        s['Unmapped']=len(val[lambda df : df.mapped == False])
        #s['Mismapped'] = len(tmp.loc[lambda df : (df.contig.str.rstrip('.ori') != df.contig_lib.str.rstrip('.ori'))& (df.mapped == True)])
        #s['Unsplit'] = len(val.loc[lambda df : (df.mapped==True)&(df.split==False)])
        #s['Missplit'] = len(val.loc[lambda df : (df.split==True)&(df.missplit==True)])
        #s['Correct splitting'] = len(val.loc[lambda df : df.classe == 'TP'])
        series.append(s)
        
        to_plot = s[['Unmapped','Unsplit','Correct splitting']]/s['Covering']*100
        fig.add_trace(
            go.Bar(
                    x=to_plot.index,
                    y=to_plot.values
            ))
    table = pd.concat(series,axis=1,sort=False)
        
    fig.update_layout(
        title='Global mapping results on introns-covering reads',
        xaxis=dict(title='Lectures charecteristics'),
        yaxis=dict(title='Percentage of total covering reads alignements')
        )

    return py.offline.plot(fig, include_plotlyjs=False, output_type='div'), table

# Return int from flagstat HISAT2/STAR mapping in string format (only for the last 3 values : Mapped, Properly paired, Singletons)
def pourcent(str_mapping:str, tot:int):
    mapping=re.sub(r'(\([a-zA-Z0-9_]*.[a-zA-Z0-9_]*%\))', r" ", str_mapping)
    val=(int(mapping)*100)/tot
    return val

# Pie Chart with mapping stats from flagstat files
def OLD_plot_flagstat(df_flag_all:dict):
    tot=int(df_flag_all.iloc[0,0])
    unmapp= round(100.00 - pourcent(df_flag_all.iloc[2,0],tot), 2)
    data = dict(
        character=["Unmapped", "Secondary","Mapped", "Properly paired", "Singletons"],
        parent=["", "Mapped", "", "Mapped", "Mapped"],
        value=[unmapp, round((int(df_flag_all.iloc[1,0])*100)/tot, 2), round(pourcent(df_flag_all.iloc[2,0],tot),2), round(pourcent(df_flag_all.iloc[3,0],tot),2), round(pourcent(df_flag_all.iloc[4,0],tot),2)])
    fig =px.sunburst(
        data,
        names='character',
        parents='parent',
        values='value',
    )
    fig.update_layout(
        margin=go.layout.Margin(
            l=50,
            r=50,
            b=20,
            t=30,
            pad=0
        )
    )

    return py.offline.plot(fig, include_plotlyjs=False, output_type='div')

#Return bar chart
    def plot_flagstat(df_flag:dict):
    

    return py.offline.plot(fig, include_plotlyjs=False, output_type='div')
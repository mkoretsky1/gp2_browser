import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from utils.hold_data import (
    blob_as_csv, 
    get_gcloud_bucket, 
    cohort_select
)

def load_qc_data():
    gp2_data_bucket = get_gcloud_bucket('gp2tier2')
    qc_metrics_path = f"{st.session_state['release_bucket']}/meta_data/qc_metrics/qc_metrics.csv"
    df_qc = blob_as_csv(gp2_data_bucket, qc_metrics_path, sep=',')

    release_choice = st.session_state['release_choice']
    master_key_path = (
        f"{st.session_state['release_bucket']}/clinical_data/master_key_release7_final.csv"
        if release_choice == 8 else
        f"{st.session_state['release_bucket']}/clinical_data/master_key_release{release_choice}_final.csv"
    )
    master_key = blob_as_csv(gp2_data_bucket, master_key_path, sep=',')

    cohort_select(master_key)

    return master_key, df_qc

def prepare_funnel_data(master_key):
    pre_QC_total = master_key['GP2sampleID'].count()
    funnel_df = pd.DataFrame(columns=['remaining_samples', 'step'])
    funnel_df.loc[0] = {'remaining_samples': pre_QC_total, 'step': 'pre_QC'}

    hold_prunes = master_key['pruned_reason'].value_counts().rename_axis('pruned_reason').reset_index(name='pruned_counts')
    remaining_samples = pre_QC_total

    ordered_prune = [
        'insufficient_ancestry_sample_n', 
        'phenotype_not_reported', 
        'missing_idat',
        'missing_bed', 
        'callrate_prune', 
        'sex_prune', 
        'het_prune', 
        'duplicated_prune'
    ]

    for prunes in ordered_prune:
        obs_pruned = hold_prunes['pruned_reason'].tolist()
        if prunes in obs_pruned:
            row = hold_prunes.loc[hold_prunes['pruned_reason'] == prunes]
            remaining_samples -= row.iloc[0]['pruned_counts']
        funnel_df.loc[len(funnel_df.index)] = {'remaining_samples': remaining_samples, 'step': prunes}

    steps_dict = {
        'pre_QC': 'Pre-QC',
        'insufficient_ancestry_sample_n': 'Insufficient Ancestry Count',
        'missing_idat': 'Missing IDAT',
        'missing_bed': 'Missing BED',
        'phenotype_not_reported': 'Phenotype Not Reported',
        'callrate_prune': 'Call Rate Prune',
        'sex_prune': 'Sex Prune',
        'duplicated_prune': 'Duplicated',
        'het_prune': 'Heterozygosity Prune'
    }
    funnel_df['step_name'] = funnel_df['step'].map(steps_dict)

    return funnel_df

def prepare_relatedness_data(master_key, ancestry_dict, ancestry_index):
    df_3 = master_key[(master_key['related'] == 1) | (master_key['pruned_reason'] == 'duplicated_prune')]
    df_3 = df_3[['label', 'pruned']]

    df_4_dicts = []
    for label in ancestry_dict:
        ancestry_df_dict = {
            'ancestry': label,
            'related_count': df_3[df_3['label'] == label][df_3['pruned'] == 0].shape[0],
            'duplicated_count': df_3[df_3['label'] == label][df_3['pruned'] == 1].shape[0]
        }
        df_4_dicts.append(ancestry_df_dict)

    df_4 = pd.DataFrame(df_4_dicts)
    df_4['label'] = df_4['ancestry'].map(ancestry_dict)
    df_4['label_index'] = df_4['ancestry'].map(ancestry_index)
    df_4.sort_values(by=['label_index'], inplace=True)
    df_4.set_index('ancestry', inplace=True)

    return df_4

def prepare_variant_data(df_qc):
    metrics = [
        'geno_removed_count', 'mis_removed_count', 
        'haplotype_removed_count', 'hwe_removed_count', 
        'total_removed_count'
    ]

    dataframes = []
    for metric in metrics:
        df_metric = df_qc.query(f"metric == '{metric}'").reset_index(drop=True)
        df_metric.rename(
            columns={'pruned_count': metric, 'metric': 'metric_type'}, 
            inplace=True
        )
        df_metric.drop(columns=['metric_type'], inplace=True)
        dataframes.append(df_metric)

    df_merged = dataframes[0]
    for df in dataframes[1:]:
        df_merged = pd.merge(
            df_merged, df, 
            on=['ancestry'], 
            how='outer', 
            suffixes=('', '_duplicate')
        )

    df_merged = df_merged.loc[:, ~df_merged.columns.duplicated()]

    df_merged.set_index('ancestry', inplace=True)
    return df_merged

def create_qc_plots(funnel_df, relatedness_df, variant_df):
    funnel_plot = go.Figure(go.Funnelarea(
        text=[f'<b>{i}</b>' for i in funnel_df['step_name']],
        values=funnel_df['remaining_samples'],
        marker={
            "colors": [
                "#999999", 
                "#E69F00", 
                "#56B4E9", 
                "#009E73", 
                "#AA4499", 
                "#F0E442", 
                "#0072B2", 
                "#D55E00", 
                "#CC79A7"
            ]
        },
        opacity=1.0, textinfo='text',
        customdata=funnel_df['remaining_samples'],
        hovertemplate='Remaining Samples:<br>%{customdata:.f}<extra></extra>'
    ))

    funnel_plot.update_layout(showlegend=False, margin=dict(l=0, r=300, t=10, b=0))

    relatedness_plot = go.Figure(
        data=[
            go.Bar(
                y=relatedness_df.label, 
                x=relatedness_df['related_count'], 
                orientation='h', 
                name="Related", 
                marker_color="#0072B2"
            ),
            go.Bar(
                y=relatedness_df.label, 
                x=-relatedness_df['duplicated_count'], 
                orientation='h', 
                name="Duplicated", 
                marker_color="#D55E00"
            )
        ]
    )

    relatedness_plot.update_layout(
        barmode='stack', 
        height=500, 
        width=750, 
        margin=dict(l=0, r=200, t=10, b=60)
    )

    variant_plot = go.Figure()
    for col, color in zip(variant_df.columns, ["#0072B2", "#882255", "#44AA99", "#D55E00"]):
        variant_plot.add_trace(
            go.Bar(
                x=variant_df.index, 
                y=variant_df[col], 
                name=col.replace('_count', ' Count'), 
                marker_color=color
            )
        )
    variant_plot.update_layout(
        barmode='stack', xaxis=dict(title='Ancestry', tickfont_size=14),
        yaxis=dict(title='Count', titlefont_size=16, tickfont_size=14),
        width=1100, height=600
    )

    return funnel_plot, relatedness_plot, variant_plot
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from utils.hold_data import (
    blob_as_csv, 
    get_gcloud_bucket, 
    get_master_key,
    cohort_select
)

def load_qc_data():
    gp2_data_bucket = get_gcloud_bucket('gt_app_utils')
    master_key = get_master_key(gp2_data_bucket)
    cohort_select(master_key)

    qc_metrics_path = f"qc_metrics/release{st.session_state['release_choice']}/qc_steps.csv"
    df_qc = blob_as_csv(gp2_data_bucket, qc_metrics_path, sep=',')

    return master_key, df_qc

def prepare_funnel_data(master_key, df_qc):
    pre_QC_total = master_key['IID'].count()

    sample_level = df_qc[df_qc.level == 'sample']
    funnel_df = sample_level.groupby('step', as_index=False)['pruned_count'].sum()
    funnel_df.loc[-1] = {'pruned_count': 0, 'step': 'pre_QC'}

    ordered_prune = {
        'pre_QC': 'Pre-QC',
        'callrate_prune': 'Call Rate Prune',
        'sex_prune': 'Sex Prune',
        'het_prune': 'Heterozygosity Prune',
        'related_prune': 'Duplicated Prune'
    }

    # Convert 'step' to categorical with the defined order and sort
    funnel_df['step'] = pd.Categorical(funnel_df['step'], categories=ordered_prune.keys(), ordered=True)
    funnel_df.sort_values('step', inplace = True)
    funnel_df['remaining_samples'] = pre_QC_total - funnel_df['pruned_count'].cumsum()
    funnel_df['step_name'] = funnel_df['step'].map(ordered_prune)

    # pre_QC_total = master_key['IID'].count()

    # funnel_df = pd.DataFrame(columns=['remaining_samples', 'step'])
    # funnel_df.loc[0] = {'remaining_samples': pre_QC_total, 'step': 'pre_QC'}

    # hold_prunes = master_key['prune_reason'].value_counts().rename_axis('prune_reason').reset_index(name='pruned_counts')
    # remaining_samples = pre_QC_total

    # ordered_prune = [
    #     'insufficient_ancestry_sample_n', 
    #     'phenotype_not_reported', 
    #     'clinical_inconsistency', 
    #     'missing_idat',
    #     'missing_bed',
    #     'callrate', 
    #     'sex', 
    #     'het', 
    #     'duplicated'
    # ]

    # for prunes in ordered_prune:
    #     obs_pruned = hold_prunes['prune_reason'].tolist()
    #     if prunes in obs_pruned:
    #         row = hold_prunes.loc[hold_prunes['prune_reason'] == prunes]
    #         remaining_samples -= row.iloc[0]['pruned_counts']
    #     funnel_df.loc[len(funnel_df.index)] = {'remaining_samples': remaining_samples, 'step': prunes}

    # steps_dict = {
    #     'pre_QC': 'Pre-QC',
    #     'insufficient_ancestry_sample_n': 'Insufficient Ancestry Count',
    #     'missing_idat': 'Missing IDAT',
    #     'missing_bed': 'Missing BED',
    #     'phenotype_not_reported': 'Phenotype Not Reported',
    #     'clinical_inconsistency': 'Clinical Inconsistency',
    #     'callrate': 'Call Rate Prune',
    #     'sex': 'Sex Prune',
    #     'duplicated': 'Duplicated Prune',
    #     'het': 'Heterozygosity Prune'
    # }
    # funnel_df['step_name'] = funnel_df['step'].map(steps_dict)

    return funnel_df

def prepare_relatedness_data(master_key, ancestry_dict, ancestry_index):
    df_3 = master_key[(master_key['related'] == 1) | (master_key['prune_reason'] == 'duplicated')]
    df_3 = df_3[['label', 'prune_reason', 'related']]

    df_4_dicts = []
    for label in ancestry_dict:
        ancestry_df_dict = {
            'ancestry': label,
            'related_count': df_3[df_3['label'] == label][df_3['related'] == 1].shape[0],
            'duplicated_count': df_3[df_3['label'] == label][df_3['prune_reason'].notnull()].shape[0]
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
        'haplotype_removed_count', 'hwe_removed_count'
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
                   "#999999",  # Gray  
                    "#E69F00",  # Orange  
                    "#56B4E9",  # Sky Blue  
                    "#009E73",  # Green  
                    "#AA4499",  # Purple  
                    "#F0E442",  # Yellow  
                    "#0072B2",  # Blue  
                    "#D55E00",  # Dark Orange  
                    "#CC79A7",  # Pink  
                    "#882255"   # Deep Red  
            ]
        },
        opacity=1.0, textinfo='text',
        customdata=funnel_df['remaining_samples'],
        hovertemplate='Remaining Samples:<br>%{customdata[0]:.f}'+'<extra></extra>'
    ))

    funnel_plot.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=10))

    relatedness_plot = go.Figure(
        data=[
            go.Bar(
                y=relatedness_df.label, 
                x=relatedness_df['related_count'], 
                orientation='h', 
                name="Related", 
                base=0,
                marker_color="#0072B2"
            ),
            go.Bar(
                y=relatedness_df.label, 
                x=-relatedness_df['duplicated_count'], 
                orientation='h', 
                name="Duplicated", 
                base=0,
                marker_color="#D55E00"
            )
        ]
    )

    relatedness_plot.update_layout(
        barmode='stack', 
        height=500, 
        width=750, 
        autosize=False,
        margin=dict(l=0, r=0, t=10, b=70)
    )

    relatedness_plot.update_yaxes(
        ticktext=relatedness_df.label,
        tickvals=relatedness_df.label
    )

    variant_plot = go.Figure()
    for col, color in zip(
        ['geno_removed_count', 'mis_removed_count', 
        'haplotype_removed_count', 'hwe_removed_count'], 
        ["#0072B2", "#882255", "#44AA99", "#D55E00"]):
        variant_plot.add_trace(
            go.Bar(
                x=variant_df.index, 
                y=variant_df[col], 
                name=col, 
                marker_color=color
            )
        )
    variant_plot.update_layout(
        barmode='stack', xaxis=dict(title='Ancestry', tickfont_size=14),
        yaxis=dict(title='Count', titlefont_size=16, tickfont_size=14),
        width=1100, height=600
    )

    return funnel_plot, relatedness_plot, variant_plot
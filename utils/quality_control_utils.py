import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from utils.hold_data import (
    blob_as_csv, 
    get_gcloud_bucket
)

def load_qc_data():
    gp2_data_bucket = get_gcloud_bucket('gt_app_utils')

    qc_metrics_path = f"qc_metrics/release{st.session_state['release_choice']}"
    funnel_df = blob_as_csv(gp2_data_bucket, f'{qc_metrics_path}/funnel_plot.csv', sep=',')
    related_df = blob_as_csv(gp2_data_bucket, f'{qc_metrics_path}/related_plot.csv', sep=',')
    variant_df = blob_as_csv(gp2_data_bucket, f'{qc_metrics_path}/variant_plot.csv', sep=',')
    variant_df.set_index('ancestry', inplace=True)

    return funnel_df, related_df, variant_df

def relatedness_plot(relatedness_df):
    relatedness_plot = go.Figure(
        data=[
            go.Bar(
                y=relatedness_df.label, 
                x=-relatedness_df['duplicated_count'], 
                orientation='h', 
                name="Duplicated", 
                marker_color="#D55E00"
            ),
            go.Bar(
                y=relatedness_df.label, 
                x=relatedness_df['related_count'], 
                orientation='h', 
                name="Related", 
                marker_color="#0072B2"
            )
        ]
    )

    relatedness_plot.update_layout(
        barmode='relative', 
        height=450, 
        width=750, 
        autosize=False,
        margin=dict(l=0, r=0, t=10, b=70)
    )

    return relatedness_plot

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
                x=-relatedness_df['duplicated_count'], 
                orientation='h', 
                name="Duplicated", 
                marker_color="#D55E00"
            ),
            go.Bar(
                y=relatedness_df.label, 
                x=relatedness_df['related_count'], 
                orientation='h', 
                name="Related", 
                marker_color="#0072B2"
            )
        ]
    )

    relatedness_plot.update_layout(
        barmode='relative', 
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
        variant_df.columns, 
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
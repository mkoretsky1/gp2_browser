import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dataclasses import dataclass

from utils.ancestry_utils import plot_pie
from utils.quality_control_utils import relatedness_plot
from utils.config import AppConfig

config = AppConfig()

def plot_age_distribution(master_key, stratify, plot2):
    master_key_age = master_key[master_key['age'].notnull()]
    if master_key_age.empty:
        plot2.info('No age values available for the selected cohort.')
        return

    if stratify == 'None':
        fig = px.histogram(master_key_age, x='age', nbins=25, color_discrete_sequence=["#332288"])
        fig.update_layout(title_text=f'<b>Age Distribution<b>')
    elif stratify == 'Sex':
        fig = px.histogram(
            master_key_age, 
            x='age', 
            color='sex', 
            nbins=25, 
            color_discrete_map={'Male':"#332288", 'Female':"#CC6677"})
        fig.update_layout(title_text=f'<b>Age Distribution by Sex<b>')
    elif stratify == 'Phenotype':
        fig = px.histogram(
            master_key_age, 
            x='age', 
            color='pheno', 
            nbins=25, 
            color_discrete_map={
                'Control':"#332288", 
                'PD':"#CC6677", 
                'Other':"#117733", 
                'Not Reported':"#D55E00"
            }
        )
        fig.update_layout(title_text=f'<b>Age Distribution by Phenotype<b>')

    plot2.plotly_chart(fig)

def display_phenotype_counts(master_key, plot1):
    master_key.rename(columns = {'pheno': 'Phenotype'}, inplace = True)
    male_pheno = master_key.loc[master_key['sex'] == 'Male', 'Phenotype']
    female_pheno = master_key.loc[master_key['sex'] == 'Female', 'Phenotype']

    combined_counts = pd.DataFrame({
        'Male': male_pheno.value_counts(),
        'Female': female_pheno.value_counts()
    })

    combined_counts['Total'] = combined_counts.sum(axis=1)
    combined_counts.fillna(0, inplace=True)
    combined_counts = combined_counts.astype(int)
    combined_counts.sort_values(by = 'Total', ascending = False, inplace = True)

    plot1.dataframe(combined_counts, use_container_width = True)

def display_ancestry(full_cohort):
    anc1, anc2 = st.columns(2, vertical_alignment = 'center')
    anc_choice =  st.session_state["meta_ancestry_choice"]

    anc_df = full_cohort.label.value_counts().reset_index()
    anc_df['Proportion'] = anc_df['count'] / anc_df['count'].sum()

    if anc_choice != 'All':
        percent_anc = anc_df[anc_df.label == anc_choice]['Proportion'].iloc[0] * 100
        anc1.metric(f"Count of {anc_choice} Samples in this Cohort", anc_df[anc_df.label == anc_choice]['count'].iloc[0])
        anc2.metric(f"Percent of {anc_choice} Samples in this Cohort", f"{percent_anc:.2f}%")
    else:
        anc_df.rename(columns = {'label': 'Ancestry Category', 'count': 'Count'}, inplace = True)
        release_pie = plot_pie(anc_df)
        anc2.plotly_chart(release_pie)
        anc_df.set_index('Ancestry Category', inplace = True)
        anc1.dataframe(anc_df['Count'], use_container_width = True)

def display_pruned_samples(pruned_key, pruned1):
    # pruned1, pruned2, pruned3, pruned4 = st.columns([1.75, 0.5, 1, 1], vertical_alignment = 'center')
    anc_choice = st.session_state["meta_ancestry_choice"]
    if anc_choice != "All":
        pruned_key = pruned_key[pruned_key["label"] == anc_choice]

    pruned_key['prune_reason'] = pruned_key['prune_reason'].map(config.PRUNE_MAP)
    pruned_steps = pruned_key.prune_reason.value_counts().reset_index()
    pruned_steps.rename(columns = {'prune_reason': 'Pruned Reason', 'count': 'Count'}, inplace = True)
    pruned_steps.set_index('Pruned Reason', inplace = True)
    # related_samples = pruned_key[pruned_key.related == 1]
    # duplicated_samples = pruned_key[pruned_key.prune_reason == 'Duplicated Prune']

    pruned1.markdown("#####")
    pruned1.markdown("##### Sample-Level Release Prep")
    pruned1.dataframe(pruned_steps, use_container_width = True)
    # pruned3.metric("Related Samples", len(related_samples))
    # pruned4.metric("Duplicated Samples", len(duplicated_samples))


def display_related_samples(pruned_key, pruned2):
    related_samples = pruned_key[pruned_key.related == 1]
    related_samples['related_count'] = 1

    duplicated_samples = pruned_key[pruned_key.prune_reason == 'Duplicated Prune']
    duplicated_samples['duplicated_count'] = 1

    relatedness_df = pd.concat([related_samples, duplicated_samples])

    if len(relatedness_df.label.unique()) > 3:
        pruned2.markdown("##### Relatedness per Ancestry")
        related_plot = relatedness_plot(relatedness_df)
        pruned2.plotly_chart(related_plot, use_container_width = True)
    else:
        pruned2.markdown("#####")
        pruned2.markdown("##### Related Samples per Ancestry")
        display_related = relatedness_df[['label', 'related']][relatedness_df.related == 1].value_counts().reset_index()
        for i in range(len(display_related)):
            pruned2.metric(f'{display_related.iloc[i, 0]} related samples', display_related.iloc[i, 2])
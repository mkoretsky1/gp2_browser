import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass

from utils.ancestry_utils import plot_pie

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
    male_pheno = master_key.loc[master_key['sex'] == 'Male', 'pheno']
    female_pheno = master_key.loc[master_key['sex'] == 'Female', 'pheno']

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

def display_pruned_samples(pruned_key):
    pruned1, pruned2, pruned3, pruned4 = st.columns([1.75, 0.5, 1, 1], vertical_alignment = 'center')
    anc_choice = st.session_state["meta_ancestry_choice"]
    if anc_choice != "All":
        pruned_key = pruned_key[pruned_key["label"] == anc_choice]

    pruned_steps = pruned_key.prune_reason.value_counts().reset_index()
    pruned_steps.rename(columns = {'prune_reason': 'Pruned Reason', 'count': 'Count'}, inplace = True)
    pruned_steps.set_index('Pruned Reason', inplace = True)
    related_samples = pruned_key[pruned_key.related == 1]
    duplicated_samples = pruned_key[pruned_key.prune_reason == 'duplicated']

    pruned1.dataframe(pruned_steps, use_container_width = True)
    pruned3.metric("Related Samples", len(related_samples))
    pruned4.metric("Duplicated Samples", len(duplicated_samples))

import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass

def plot_age_distribution(master_key, plot1, plot2):
    master_key_age = master_key[master_key['age'].notnull()]
    if master_key_age.empty:
        return

    plot1.markdown('#### Stratify Age by:')
    stratify = plot1.radio("Stratify Age by:", ('None', 'Sex', 'Phenotype'), label_visibility="collapsed")

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
    plot1.markdown('---')

def display_phenotype_counts(master_key, plot1):
    male_pheno = master_key.loc[master_key['sex'] == 'Male', 'pheno']
    female_pheno = master_key.loc[master_key['sex'] == 'Female', 'pheno']

    combined_counts = pd.DataFrame({
        'Male': male_pheno.value_counts(),
        'Female': female_pheno.value_counts()
    }).transpose()

    combined_counts['Total'] = combined_counts.sum(axis=1)
    combined_counts.fillna(0, inplace=True)
    combined_counts = combined_counts.astype(int)

    plot1.markdown('#### Phenotype Count Split by Sex')
    plot1.dataframe(combined_counts)
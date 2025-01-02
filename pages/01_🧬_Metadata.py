import streamlit as st
import pandas as pd
from utils.data_loader import DataLoader
from utils.data_processor import DataProcessor
from visualization.plotters import MetadataPlotter
from hold_data import get_gcloud_bucket, config_page, cohort_select, release_select, meta_ancestry_select

def main():

    config_page('Metadata')
    release_select()

    gp2_data_bucket = get_gcloud_bucket('gp2tier2')
    data_loader = DataLoader(gp2_data_bucket)

    master_key = data_loader.get_master_key(
        st.session_state['release_choice'],
        st.session_state['release_bucket']
    )
    cohort_select(master_key)

    st.title(f'{st.session_state["cohort_choice"]} Metadata')

    processor = DataProcessor()
    master_key = processor.process_master_key(
        st.session_state['master_key'],
        st.session_state['release_choice']
    )

    meta_ancestry_select()
    if st.session_state['meta_ancestry_choice'] != 'All':
        master_key = master_key[master_key['label'] == st.session_state['meta_ancestry_choice']]

    plot1, plot2 = st.columns([1, 1.75])

    master_key_age = master_key[master_key['Age'].notnull()]
    if master_key_age.shape[0] != 0:
        plot1.markdown('#### Stratify Age by:')
        stratify = plot1.radio(
            "Stratify Age by:",
            ('None', 'Sex', 'Phenotype'),
            label_visibility="collapsed"
        )
        
        plotter = MetadataPlotter()
        fig = plotter.plot_age_distribution(master_key, stratify)
        plot2.plotly_chart(fig)
        plot1.markdown('---')

    plot1.markdown('#### Phenotype Count Split by Sex')
    combined_counts = processor.get_phenotype_counts(master_key)
    plot1.dataframe(combined_counts)

if __name__ == "__main__":
    main()
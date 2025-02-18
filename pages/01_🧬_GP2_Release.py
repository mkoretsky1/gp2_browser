import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from utils.hold_data import (
    get_gcloud_bucket,  
    release_select, 
    config_page,
    get_master_key,
    filter_by_cohort,
    filter_by_ancestry,
    update_sex_labels,
)
from utils.metadata_utils import display_ancestry, plot_age_distribution, display_phenotype_counts, display_pruned_samples, display_related_samples
from utils.config import AppConfig

config = AppConfig()

def main():
    config_page('GP2 Release')
    
    release_select()
    gp2_data_bucket = get_gcloud_bucket('gt_app_utils')
    master_key = get_master_key(gp2_data_bucket)
    master_key_cohort = filter_by_cohort(master_key)
    pruned_key = st.session_state['master_key']
    st.session_state['master_key'] = master_key_cohort

    st.title(f"{st.session_state['cohort_choice']} Metadata")
    st.markdown('## :blue[Ancestry Breakdown]')

    master_key = filter_by_ancestry(master_key_cohort)
    master_key = update_sex_labels(master_key)
    display_ancestry(master_key_cohort)

    st.markdown('---')
    st.markdown('## :blue[Age Breakdown]')
    st.markdown('#### Stratify Age by:')
    stratify = st.selectbox("Stratify Age by:", options = ['None', 'Sex', 'Phenotype'], label_visibility="collapsed")

    plot1, plot2 = st.columns([1, 1.75], vertical_alignment = 'center')

    plot_age_distribution(master_key, stratify, plot2)
    display_phenotype_counts(master_key, plot1)
    st.markdown('---')

    st.markdown('## :blue[QC Breakdown]')  
    pruned1, pruned2 = st.columns([1, 1.75])
    pruned_key['prune_reason'] = pruned_key['prune_reason'].map(config.PRUNE_MAP)
    display_pruned_samples(pruned_key, pruned1)
    display_related_samples(pruned_key, pruned2)


if __name__ == "__main__":
    main()

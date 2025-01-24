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
    rename_columns,
    update_sex_labels
)
from utils.metadata_utils import plot_age_distribution, display_phenotype_counts

def main():
    config_page('Metadata')
    
    release_select()
    gp2_data_bucket = get_gcloud_bucket('gp2tier2')
    
    master_key = get_master_key(gp2_data_bucket)
    master_key = filter_by_cohort(master_key)
    master_key = filter_by_ancestry(master_key)
    master_key = rename_columns(master_key)
    master_key = update_sex_labels(master_key)

    st.session_state['master_key'] = master_key
    st.title(f"{st.session_state['cohort_choice']} Metadata")

    plot1, plot2 = st.columns([1, 1.75])
    plot_age_distribution(master_key, plot1, plot2)
    display_phenotype_counts(master_key, plot1)

if __name__ == "__main__":
    main()

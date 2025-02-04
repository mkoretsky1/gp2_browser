import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from utils.hold_data import (
    blob_as_csv,
    get_gcloud_bucket,
    get_master_key,
    filter_by_cohort,
    release_select,
    config_page
)
from utils.ancestry_utils import (
    render_tab_pca,
    render_tab_admix,
    render_tab_pie,
    render_tab_pred_stats
)
from utils.config import AppConfig

config = AppConfig()

def main():
    """
    Main function to set up the Streamlit page and render all Ancestry-related tabs.
    """
    config_page('Ancestry')
    release_select()

    ### old code before path refactor
    gp2_data_bucket = get_gcloud_bucket('gt_app_utils') # used to be gp2tier2
    # master_key = get_master_key(gp2_data_bucket)
    # cohort_select(master_key)

    # pca_folder = f"{st.session_state['release_bucket']}/meta_data/qc_metrics"
    # master_key = st.session_state['master_key']
    # master_key = master_key[master_key['pruned'] == 0]

    master_key = get_master_key(gp2_data_bucket)
    master_key = filter_by_cohort(master_key)
    pca_folder = f"qc_metrics/release{st.session_state['release_choice']}"

    tab_pca, tab_pred_stats, tab_pie, tab_admix, tab_methods = st.tabs([
        "Ancestry Prediction",
        "Model Performance",
        "Ancestry Distribution",
        "Admixture Populations",
        "Method Description"
    ])

    with tab_pca:
        render_tab_pca(pca_folder, gp2_data_bucket, master_key)

    with tab_pred_stats:
        render_tab_pred_stats(pca_folder, gp2_data_bucket)

    with tab_pie:
        render_tab_pie(pca_folder, gp2_data_bucket)

    with tab_admix:
        render_tab_admix()

    with tab_methods:
        st.markdown(config.DESCRIPTIONS['ancestry_methods'])


if __name__ == "__main__":
    main()

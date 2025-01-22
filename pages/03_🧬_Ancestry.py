import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from utils.hold_data import (
    blob_as_csv,
    get_gcloud_bucket,
    cohort_select,
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

    gp2_data_bucket = get_gcloud_bucket('gp2tier2')

    if st.session_state['release_choice'] == 8:
        master_key_path = (
            f"{st.session_state['release_bucket']}/clinical_data/"
            "master_key_release7_final.csv"
        )
    else:
        master_key_path = (
            f"{st.session_state['release_bucket']}/clinical_data/"
            f"master_key_release{st.session_state['release_choice']}_final.csv"
        )

    master_key = blob_as_csv(gp2_data_bucket, master_key_path, sep=',')
    cohort_select(master_key)

    pca_folder = f"{st.session_state['release_bucket']}/meta_data/qc_metrics"
    master_key = st.session_state['master_key']
    master_key = master_key[master_key['pruned'] == 0]

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

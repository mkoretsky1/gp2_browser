import streamlit as st
import pandas as pd
from utils.utils import get_gcloud_bucket, blob_as_csv

def load_master_key() -> pd.DataFrame:
    """
    Load master key data based on the current release in session_state.
    """
    release_choice = st.session_state["release_choice"]
    master_key_path = f"release_keys/master_key_release{release_choice}_app.csv"
    try:
        return blob_as_csv(st.session_state["gt_app_utils_bucket"], master_key_path, sep=",")
    except Exception:
        st.error(f"Master key for Release {release_choice} could not be found. Please select a different release.")
        st.stop()

def initialize_state():
    """
    Initialize all session_state variables only if they don't already exist
    so that the chosen release persists across pages.
    """
    if "initialized" not in st.session_state:
        st.session_state["initialized"] = True
    if "gt_app_utils_bucket" not in st.session_state:
        st.session_state["gt_app_utils_bucket"] = get_gcloud_bucket("gt_app_utils")
    if "release_choice" not in st.session_state:
        st.session_state["release_choice"] = "9"
    if "cohort_choice" not in st.session_state:
        st.session_state["cohort_choice"] = f"GP2 Release {st.session_state['release_choice']} FULL"
    if "master_key" not in st.session_state:
        st.session_state["master_key"] = load_master_key()
    if "release_qc_path" not in st.session_state:
        st.session_state["release_qc_path"] = f'qc_metrics/release{st.session_state["release_choice"]}'
    if "release_qc_bucket" not in st.session_state:
        st.session_state["release_qc_bucket"] = (
            f'{st.session_state["gt_app_utils_bucket"]}/qc_metrics/release{st.session_state["release_choice"]}'
        )

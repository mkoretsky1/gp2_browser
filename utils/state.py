import streamlit as st
import pandas as pd
from utils.utils import get_gcloud_bucket, blob_as_csv, load_master_key, filter_master_key


def initialize_state():
    if "initialized" not in st.session_state:
        st.session_state["initialized"] = True
        # st.session_state["gp2_data_bucket"] = get_gcloud_bucket("gp2tier2")
        st.session_state["gt_app_utils_bucket"] = get_gcloud_bucket("gt_app_utils")
        st.session_state["release_choice"] = "8"  # Default to the latest release
        # release_folder_dict = {'1':'release1_29112021', '2':'release2_06052022', '3':'release3_31102022', '4':'release4_14022023', 
        #                    '5':'release5_11052023', '6':'release6_21122023', '7':'release7_30042024', '8':'release7_30042024'}
        # st.session_state['release_bucket'] = release_folder_dict[st.session_state['release_choice']]
        st.session_state['release_qc_path'] = f'qc_metrics/release{st.session_state["release_choice"]}'
        st.session_state['release_qc_bucket'] = f'{st.session_state["gt_app_utils_bucket"]}/qc_metrics/release{st.session_state["release_choice"]}'
        st.session_state["cohort_choice"] = f'GP2 Release {st.session_state["release_choice"]} FULL'  # Default to all cohorts
        st.session_state["master_key"] = load_master_key()
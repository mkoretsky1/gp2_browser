import streamlit as st
from typing import Optional
import pandas as pd
from hold_data import get_gcloud_bucket, blob_as_csv

def init_session_state():
    """Initialize session state variables if they don't exist"""
    if 'data_cache' not in st.session_state:
        st.session_state['data_cache'] = {
            'master_key': None,
            'qc_metrics': None,
            'last_release': None
        }

class DataStateManager:
    """
    Singleton class to manage data state across pages.
    Handles data loading, caching, and state updates.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataStateManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.gp2_data_bucket = get_gcloud_bucket('gp2tier2')
        self.gt_app_utils_bucket = get_gcloud_bucket('gt_app_utils')
        
        init_session_state()

    def _load_master_key(self) -> pd.DataFrame:
        """Load master key data based on current release"""
        release_choice = st.session_state['release_choice']
        master_key_path = f'release_keys/master_key_release{release_choice}_app.csv'
        return blob_as_csv(self.gt_app_utils_bucket, master_key_path, sep=',')

    def _load_qc_metrics(self) -> pd.DataFrame:
        """Load QC metrics data"""
        release_bucket = st.session_state['release_bucket']
        qc_metrics_path = f'{release_bucket}/meta_data/qc_metrics/qc_metrics.csv'
        return blob_as_csv(self.gp2_data_bucket, qc_metrics_path, sep=',')

    def get_master_key(self) -> pd.DataFrame:
        """Get master key data, reloading if release has changed"""
        current_release = st.session_state['release_choice']
        
        if (st.session_state['data_cache']['last_release'] != current_release or 
            st.session_state['data_cache']['master_key'] is None):
            st.session_state['data_cache']['master_key'] = self._load_master_key()
            st.session_state['data_cache']['last_release'] = current_release
            
        return st.session_state['data_cache']['master_key']

    def get_qc_metrics(self) -> pd.DataFrame:
        """Get QC metrics data, reloading if needed"""
        current_release = st.session_state['release_choice']
        
        if (st.session_state['data_cache']['last_release'] != current_release or 
            st.session_state['data_cache']['qc_metrics'] is None):
            st.session_state['data_cache']['qc_metrics'] = self._load_qc_metrics()
            
        return st.session_state['data_cache']['qc_metrics']

    def clear_cache(self):
        """Clear the data cache"""
        st.session_state['data_cache'] = {
            'master_key': None,
            'qc_metrics': None,
            'last_release': None
        }






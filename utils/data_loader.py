from typing import Tuple, Optional
import pandas as pd
from hold_data import blob_as_csv

class DataLoader:
    def __init__(self, gp2_data_bucket):
        self.gp2_data_bucket = gp2_data_bucket
    
    def get_master_key(self, release_choice: int, release_bucket: str) -> pd.DataFrame:
        """Load master key based on release choice"""
        if release_choice == 8:
            master_key_path = f'{release_bucket}/clinical_data/master_key_release7_final.csv'
        else:
            master_key_path = f'{release_bucket}/clinical_data/master_key_release{release_choice}_final.csv'
        return blob_as_csv(self.gp2_data_bucket, master_key_path, sep=',')

    def get_qc_metrics(self, release_bucket: str) -> pd.DataFrame:
        """Load QC metrics data"""
        qc_metrics_path = f'{release_bucket}/meta_data/qc_metrics/qc_metrics.csv'
        return blob_as_csv(self.gp2_data_bucket, qc_metrics_path, sep=',')

import streamlit as st
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional

from hold_data import (
    blob_as_csv,
    get_gcloud_bucket,
    cohort_select,
    release_select,
    config_page,
    meta_ancestry_select,
)

class AppConfig:
    """config settings for the application."""
    CARRIERS_BUCKET_NAME: str = 'gp2_carriers'
    GP2_DATA_BUCKET_NAME: str = 'gp2tier2'
    CARRIERS_FILE_PATH: str = 'carriers_string_full.csv'
    NON_VARIANT_COLUMNS: List[str] = ['GP2ID', 'ancestry']
    WILD_TYPE: str = 'WT/WT'
    MISSING_GENOTYPE: str = './.'

class GenotypeMatcher:
    """handler for genotype matching and carrier status"""
    
    @staticmethod
    def is_carrier(genotype: str) -> bool:
        """check if a genotype indicates carrier status"""
        return genotype not in [AppConfig.WILD_TYPE, AppConfig.MISSING_GENOTYPE]

    @staticmethod
    def is_homozygous(genotype: str) -> bool:
        """check if a genotype is homozygous"""
        if genotype == AppConfig.MISSING_GENOTYPE:
            return False
        alleles = genotype.split('/')
        return alleles[0] == alleles[1] and alleles[0] != "."

class CarrierDataProcessor:
    """processes carrier data and manages carrier status determination"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.variants = self._get_variants()

    def _get_variants(self) -> List[str]:
        """xtract variant columns from the dataframe"""
        return [col for col in self.df.columns if col not in AppConfig.NON_VARIANT_COLUMNS]

    def get_carrier_status(self, row: pd.Series, selected_variants: List[str], 
                          zygosity_filter: str = 'All') -> Dict[str, str]:
        """determine carrier status for a given row based on selected variants and zygosity filter"""
        status = {}
        has_carrier = False
        
        for variant in selected_variants:
            if variant in row:
                genotype = row[variant]
                if GenotypeMatcher.is_carrier(genotype):
                    if self._matches_zygosity_filter(genotype, zygosity_filter):
                        has_carrier = True

        if has_carrier:
            status = {variant: row[variant] for variant in selected_variants if variant in row}
        
        return status

    def _matches_zygosity_filter(self, genotype: str, zygosity_filter: str) -> bool:
        """check if genotype matches the selected zygosity filter"""
        if zygosity_filter == 'All':
            return True
        if zygosity_filter == 'Homozygous':
            return GenotypeMatcher.is_homozygous(genotype)
        if zygosity_filter == 'Heterozygous':
            return not GenotypeMatcher.is_homozygous(genotype)
        return False

    def filter_by_ancestry(self, ancestry: str) -> pd.DataFrame:
        """filter dataframe by ancestry"""
        if ancestry != 'All':
            return self.df[self.df['ancestry'] == ancestry]
        return self.df

    def process_carriers(self, selected_variants: List[str], ancestry: str, 
                        zygosity_filter: str) -> Optional[pd.DataFrame]:
        """process and return carrier data based on selected filters"""
        if not selected_variants:
            return None

        working_df = self.filter_by_ancestry(ancestry)
        carriers_status = []

        for _, row in working_df.iterrows():
            has_variant = any(GenotypeMatcher.is_carrier(row[variant]) 
                            for variant in selected_variants)

            if has_variant:
                status = self.get_carrier_status(row, selected_variants, zygosity_filter)
                if status:
                    carriers_status.append({
                        'GP2ID': row['GP2ID'],
                        'ancestry': row['ancestry'],
                        **status
                    })

        return pd.DataFrame(carriers_status) if carriers_status else None

def get_master_key_path(release_bucket: str, release_choice: int) -> str:
    """generate the master key path based on release choice"""
    if release_choice == 8:
        return f'{release_bucket}/clinical_data/master_key_release7_final.csv'
    return f'{release_bucket}/clinical_data/master_key_release{release_choice}_final.csv'

def setup_page() -> None:
    """config the page and initialize session state"""
    config_page('Carriers')
    release_select()

def main():
    setup_page()
    
    # iunitialize buckets
    gp2_data_bucket = get_gcloud_bucket(AppConfig.GP2_DATA_BUCKET_NAME)
    carriers_bucket = get_gcloud_bucket(AppConfig.CARRIERS_BUCKET_NAME)
    
    master_key_path = get_master_key_path(
        st.session_state["release_bucket"],
        st.session_state['release_choice']
    )
    
    master_key = blob_as_csv(gp2_data_bucket, master_key_path, sep=',')
    cohort_select(master_key)

    st.title("Genetic Variant Carrier Status Viewer")

    # load carriers data
    df = blob_as_csv(carriers_bucket, AppConfig.CARRIERS_FILE_PATH, sep=',')
    processor = CarrierDataProcessor(df)

    # ui controls
    meta_ancestry_select()
    selected_ancestry = st.session_state['meta_ancestry_choice']
    
    show_all_carriers = st.checkbox("Show All Carriers")
    zygosity_filter = st.radio("Filter by Zygosity", ['All', 'Homozygous', 'Heterozygous'])
    
    selected_variants = processor.variants if show_all_carriers else st.multiselect(
        "Choose variants to display",
        processor.variants
    )

    # display results
    if selected_variants:
        status_df = processor.process_carriers(selected_variants, selected_ancestry, zygosity_filter)
        
        if status_df is not None:
            st.header(f"Carriers Found: {len(status_df)}")
            st.dataframe(status_df)

            csv_filtered = status_df.to_csv(index=False)
            st.download_button(
                label="Download filtered dataset",
                data=csv_filtered,
                file_name=f"carriers_{selected_ancestry.lower()}_{zygosity_filter.lower()}.csv",
                mime="text/csv",
                key="download_filtered"
            )
            
        else:
            st.info(f"No {zygosity_filter.lower()} carriers found for selected variants.")
    else:
        st.info("Please select variants to view carrier status.")

    # download button
    csv_full = df.to_csv(index=False)
    st.download_button(
        label="Download complete dataset",
        data=csv_full,
        file_name="complete_dataset.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
import streamlit as st
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional

from utils.hold_data import (
    blob_as_csv,
    get_gcloud_bucket,
    get_master_key,
    filter_by_cohort,
    meta_ancestry_select,
    config_page,
    release_select
)

from utils.carriers_utils import (
    CarriersConfig,
    CarrierDataProcessor
)

from utils.config import AppConfig

config = AppConfig()

def main():
    config_page("GP2 Carriers Browser")
    release_select()

    # initialize buckets
    gp2_data_bucket = get_gcloud_bucket(CarriersConfig.GP2_DATA_BUCKET_NAME)

    master_key = get_master_key(gp2_data_bucket)
    master_key = filter_by_cohort(master_key)

    st.title("Genetic Variant Carrier Status Viewer")

    # load carriers data - subset by samples in master key
    carriers_df_in = blob_as_csv(gp2_data_bucket, CarriersConfig.CARRIERS_FILE_PATH, sep=',')
    carriers_df = carriers_df_in.loc[carriers_df_in.IID.isin(master_key.IID)]
    snp_cols = [col for col in carriers_df.columns if col not in CarriersConfig.NON_VARIANT_COLUMNS]
    filtered_carriers_df = carriers_df[carriers_df[snp_cols].apply(
    lambda row: any(val not in ["WT/WT", "./."] for val in row),
    axis=1
    )]

    processor = CarrierDataProcessor(filtered_carriers_df)

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
    csv_full = carriers_df_in.to_csv(index=False)
    st.download_button(
        label="Download complete dataset",
        data=csv_full,
        file_name="complete_dataset.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
import streamlit as st
import pandas as pd
import numpy as np

from hold_data import blob_as_csv, get_gcloud_bucket, cohort_select, release_select, config_page, meta_ancestry_select

config_page('Carriers')

release_select()

gp2_data_bucket = get_gcloud_bucket('gp2tier2')

if st.session_state['release_choice'] == 8:
    master_key_path = f'{st.session_state["release_bucket"]}/clinical_data/master_key_release7_final.csv'
else:
    master_key_path = f'{st.session_state["release_bucket"]}/clinical_data/master_key_release{st.session_state["release_choice"]}_final.csv'
master_key = blob_as_csv(gp2_data_bucket, master_key_path, sep=',')
cohort_select(master_key)

st.title("Genetic Variant Carrier Status Viewer")

# carriers_path = f'{st.session_state["release_bucket"]}/data/outputs/carriers_string_full.csv'
# df = blob_as_csv(gp2_data_bucket, carriers_path, sep=',')
def load_data():
    df = pd.read_csv('/home/vitaled2/gp2_carriers/data/outputs/carriers_string_full.csv')
    return df

df = load_data()
variants = [col for col in df.columns if col not in ["GP2ID", "ancestry"]]



meta_ancestry_select()
selected_ancestry = st.session_state['meta_ancestry_choice']

show_all_carriers = st.checkbox("Show All Carriers")

zygosity_filter = st.radio(
    "Filter by Zygosity",
    ['All', 'Homozygous', 'Heterozygous']
)

if show_all_carriers:
    selected_variants = variants
else:
    selected_variants = st.multiselect(
        "Choose variants to display",
        variants
    )

def is_carrier(genotype):
    return genotype not in ["WT/WT", "./."]

def is_homozygous(genotype):
    if genotype in ["./."]:
        return False
    alleles = genotype.split('/')
    return alleles[0] == alleles[1] and alleles[0] != "."

def get_carrier_status(row, selected_variants, zygosity_filter='All'):
    status = {}
    has_carrier = False
    
    for variant in selected_variants:
        if variant in row:
            genotype = row[variant]
            if genotype not in ["WT/WT", "./."]:
                if zygosity_filter == 'All':
                    has_carrier = True
                elif zygosity_filter == 'Homozygous' and is_homozygous(genotype):
                    has_carrier = True
                elif zygosity_filter == 'Heterozygous' and not is_homozygous(genotype):
                    has_carrier = True

    if has_carrier:
        for variant in selected_variants:
            if variant in row:
                status[variant] = row[variant]
    
    return status if has_carrier else {}

if selected_variants:
    working_df = df.copy()
    
    if selected_ancestry != 'All':
        working_df = working_df[working_df['ancestry'] == selected_ancestry]
        
    carriers_status = []
    for _, row in working_df.iterrows():
        has_variant = any(row[variant] not in ["WT/WT", "./."] for variant in selected_variants)

        if has_variant:
            status = get_carrier_status(row, selected_variants, zygosity_filter)
            if status:
                carriers_status.append({
                    'GP2ID': row['GP2ID'],
                    'ancestry': row['ancestry'],
                    **status
                })
                
    if carriers_status:
        status_df = pd.DataFrame(carriers_status)
        
        st.header(f"Carriers Found: {len(status_df)}")
        st.dataframe(status_df)
    
    else:
        st.info(f"No {zygosity_filter.lower()} carriers found for selected variants.")
else:
    st.info("Please select variants to view carrier status.")

csv_full = df.to_csv(index=False)
st.download_button(
    label="Download complete dataset",
    data=csv_full,
    file_name="complete_dataset.csv",
    mime="text/csv"
)

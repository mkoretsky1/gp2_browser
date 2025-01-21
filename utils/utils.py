import streamlit as st
import pandas as pd
from google.cloud import storage
import plotly.express as px
from dataclasses import dataclass
from io import StringIO

# Initialize a GCS client
storage_client = storage.Client()


def get_gcloud_bucket(bucket_name: str):
    """
    Get a bucket from Google Cloud Storage

    Parameters
    ----------
    bucket_name : str
        Name of the bucket to get

    Returns
    -------
    storage.bucket.Bucket
        Bucket object
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    return bucket


def blob_as_csv(bucket, path, sep=",", header="infer"):
    """
    Read a blob from a bucket and return a pandas DataFrame

    Parameters
    ----------
    bucket : storage.bucket.Bucket
        Bucket object
    path : str
        Path to the blob in the bucket
    sep : str, optional
        Delimiter to use, by default ","
    header : int, 'infer', or None, optional
        Row number(s) to use as the column names, and the start of the
        data, by default "infer"

    Returns
    -------
    pd.DataFrame
        DataFrame containing the data from the blob
    """
    blob = bucket.blob(path)
    data = blob.download_as_string()
    df = pd.read_csv(StringIO(data.decode("utf-8")), sep=sep, header=header)
    return df


def place_logos():
    sidebar1, sidebar2 = st.sidebar.columns(2)
    if ('card_removebg' in st.session_state) and ('redlat' in st.session_state):
        sidebar1.image(st.session_state.card_removebg, use_container_width=True)
        sidebar2.image(st.session_state.gp2_removebg, use_container_width=True)
        st.sidebar.image(st.session_state.redlat, use_container_width=True)
    else:
        frontend_bucket_name = 'gt_app_utils'
        frontend_bucket = get_gcloud_bucket(frontend_bucket_name)
        card_removebg = frontend_bucket.get_blob('card-removebg.png')
        card_removebg = card_removebg.download_as_bytes()
        gp2_removebg = frontend_bucket.get_blob('gp2_2-removebg.png')
        gp2_removebg = gp2_removebg.download_as_bytes()
        redlat = frontend_bucket.get_blob('Redlat.png')
        redlat = redlat.download_as_bytes()
        st.session_state['card_removebg'] = card_removebg
        st.session_state['gp2_removebg'] = gp2_removebg
        st.session_state['redlat'] = redlat
        sidebar1.image(card_removebg, use_container_width=True)
        sidebar2.image(gp2_removebg, use_container_width=True)
        st.sidebar.image(redlat, use_container_width=True)


def debug_dataframe(df):
    if st.session_state["debug_mode"]:
        st.markdown("Debug Dataframe")
        st.write(df)

# def update_master_key():
#     st.session_state["master_key"] = load_master_key()

def update_release():
    """
    Callback that updates both the release choice and the default cohort
    whenever the user picks a new release.
    """
    # This will automatically set release_choice to the newly selected value
    # (because of the key="release_choice" in the st.selectbox),
    # then reset cohort_choice to match the new release.
    st.session_state["cohort_choice"] = f'GP2 Release {st.session_state["release_choice"]} FULL'
    # st.session_state["master_key"] = load_master_key()

def get_sidebar(obj):
    """
    Build the sidebar controls so that session_state["release_choice"] 
    persists across pages. The selectbox is keyed to "release_choice" and 
    sets its index to the current value in session_state if present.
    """
    with st.sidebar:
        st.markdown('<p class="subheader-text">GP2 Release Version</p>', unsafe_allow_html=True)

        # Ensure the selectbox reflects the current release in session_state
        possible_releases = ["9", "8", "7", "6", "5", "4", "3", "2", "1"]
        if st.session_state["release_choice"] in possible_releases:
            release_index = possible_releases.index(st.session_state["release_choice"])
        else:
            # Fallback if somehow the release_choice is not in the list
            release_index = 0

        obj.selected_release = st.selectbox(
            "Choose Release",
            possible_releases,
            index=release_index,            # Let the selectbox match current session_state
            key="release_choice",           # Link to session_state["release_choice"]
            on_change=update_release        # If changed, update the cohort choice
        )

        st.markdown('<p class="subheader-text">GP2 Cohort</p>', unsafe_allow_html=True)
        master_key = st.session_state["master_key"]
        obj.selected_cohort = st.selectbox(
            "Choose Cohort",
            [f'GP2 Release {st.session_state["release_choice"]} FULL']
            + sorted(master_key['study'].unique()),
            label_visibility="collapsed",
            key="cohort_choice"
        )
        place_logos()


# def load_master_key() -> pd.DataFrame:
#     """
#     Load master key data based on current release.
#     """
#     release_choice = st.session_state["release_choice"]
#     master_key_path = f"release_keys/master_key_release{release_choice}_app.csv"
#     try:
#         master_key_df = blob_as_csv(
#             st.session_state["gt_app_utils_bucket"], master_key_path, sep=","
#         )
#     except:
#         st.error(f"Master key for Release {release_choice} could not be found. Please select a different release.")
#         st.stop()
#     return master_key_df

def filter_master_key(master_key: pd.DataFrame) -> pd.DataFrame:
    """
    Filter the master key based on selected cohort and other criteria.
    """
    cohort_choice = st.session_state["cohort_choice"]
    release_choice = st.session_state["release_choice"]

    # First, guard against mismatched "GP2 Release X FULL" states.
    # If the user had "GP2 Release 8 FULL" in session state
    # but the release_choice is now "9", reset cohort_choice to match.
    if cohort_choice.startswith("GP2 Release") and not cohort_choice.endswith(f"{release_choice} FULL"):
        st.session_state["cohort_choice"] = f"GP2 Release {release_choice} FULL"
        cohort_choice = st.session_state["cohort_choice"]

    # If the selected cohort is the "FULL" option, return the entire master_key
    if cohort_choice == f"GP2 Release {release_choice} FULL":
        return master_key

    # Otherwise, filter by the chosen study (cohort).
    if cohort_choice != "all":
        if cohort_choice not in master_key["study"].unique():
            st.error(
                f"Cohort {cohort_choice} is not available in Release {release_choice}. "
                "Please select a different cohort."
            )
            st.stop()
        master_key = master_key[master_key["study"] == cohort_choice]

    return master_key

# @dataclass
# class MetadataPlotter:
#     def plot_age_distribution(
#         self, df: pd.DataFrame, stratify_by: str, phenotype_column: str = "baseline_GP2_phenotype_for_qc"
#     ) -> px.scatter:
#         """
#         Generate an age distribution plot, optionally stratified.

#         Parameters
#         ----------
#         df : pd.DataFrame
#             Input DataFrame containing age and other relevant columns.
#         stratify_by : str
#             Column name to use for stratification ('None', 'Sex', or 'Phenotype').
#         phenotype_column : str
#             Column name for phenotype.

#         Returns
#         -------
#         px.scatter
#             A Plotly scatter plot object.
#         """
#         df['biological_sex_for_qc'] = df['biological_sex_for_qc'].replace('Unknown', 'Other')
#         if stratify_by == "None":
#             fig = px.histogram(
#                 df,
#                 x="age_at_sample_collection",
#                 title="Age Distribution",
#                 labels={"age_at_sample_collection": "Age at Sample Collection"},
#                 color_discrete_sequence=px.colors.qualitative.Set2,
#             )
#         elif stratify_by == "Sex":
#             fig = px.histogram(
#                 df,
#                 x="age_at_sample_collection",
#                 color="biological_sex_for_qc",
#                 title=f"Age Distribution (Stratified by {stratify_by})",
#                 labels={"age_at_sample_collection": "Age at Sample Collection", "biological_sex_for_qc": "Sex"},
#                 color_discrete_sequence=px.colors.qualitative.Set2,
#             )
#         elif stratify_by == "Phenotype":
#             fig = px.histogram(
#                 df,
#                 x="age_at_sample_collection",
#                 color=phenotype_column,
#                 title=f"Age Distribution (Stratified by {stratify_by})",
#                 labels={"age_at_sample_collection": "Age at Sample Collection", phenotype_column: "Phenotype"},
#                 color_discrete_sequence=px.colors.qualitative.Set2,
#             )

#         fig.update_layout(
#             xaxis_title="Age at Sample Collection",
#             yaxis_title="Count",
#             bargap=0.2,
#             legend_title=stratify_by if stratify_by != "None" else "",
#         )

#         return fig


# @dataclass
# class MetadataProcessor:
#     def get_phenotype_counts(self, df: pd.DataFrame, phenotype_column: str = "baseline_GP2_phenotype_for_qc") -> pd.DataFrame:
#         """
#         Calculate phenotype counts, optionally split by sex.

#         Parameters
#         ----------
#         df : pd.DataFrame
#             Input DataFrame containing 'Phenotype' and 'Sex' columns.
#         phenotype_column : str
#             Column name for phenotype.

#         Returns
#         -------
#         pd.DataFrame
#             DataFrame with phenotype counts, optionally split by sex.
#         """
#         df['biological_sex_for_qc'] = df['biological_sex_for_qc'].replace('Unknown', 'Other')
#         if phenotype_column not in df.columns:
#             st.error(
#                 f"'{phenotype_column}' column not found in the DataFrame for Release {st.session_state['release_choice']}. "
#                 "Please select a different release."
#             )
#             st.stop()
            
#         if "biological_sex_for_qc" not in df.columns:
#             counts = df[phenotype_column].value_counts().reset_index()
#             counts.columns = [phenotype_column, "Count"]
#         else:
#             counts = (
#                 df.groupby([phenotype_column, "biological_sex_for_qc"])
#                 .size()
#                 .reset_index(name="Count")
#             )
#             counts = counts.pivot(
#                 index=phenotype_column, columns="biological_sex_for_qc", values="Count"
#             ).reset_index()
#             counts.columns.name = None  # Remove the 'Sex' name from columns

#         return counts
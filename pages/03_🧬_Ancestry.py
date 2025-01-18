import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px

from utils.state import initialize_state
from utils.utils import (
    get_sidebar,
    filter_master_key,
    blob_as_csv,
    get_gcloud_bucket,
)

initialize_state()

def plot_3d(
    labeled_df: pd.DataFrame,
    color: str,
    symbol: str = None,
    x: str = 'PC1',
    y: str = 'PC2',
    z: str = 'PC3',
    title: str = None,
    x_range=None,
    y_range=None,
    z_range=None
):
    """
    3D scatter plot of PCA components.
    """
    fig = px.scatter_3d(
        labeled_df,
        x=x,
        y=y,
        z=z,
        color=color,
        symbol=symbol,
        title=title,
        color_discrete_sequence=px.colors.qualitative.Bold,
        range_x=x_range,
        range_y=y_range,
        range_z=z_range,
        hover_name="IID",
        color_discrete_map={
            'AFR': "#88CCEE",
            'SAS': "#CC6677",
            'EAS': "#DDCC77",
            'EUR': "#117733",
            'AMR': "#332288",
            'AJ':  "#D55E00",
            'AAC': "#999933",
            'CAS': "#882255",
            'MDE': "#661100",
            'FIN': "#F0E442",
            'CAH': "#40B0A6",
            'Predicted': "#ababab"
        }
    )
    fig.update_traces(marker={'size': 3})
    st.plotly_chart(fig)

def admix_ancestry_select():
    st.markdown("### **Choose an ancestry!**")
    master_key = st.session_state["master_key"]

    # Gather all ancestry options (including 'All')
    admix_ancestry_options = ["All"] + sorted(master_key["nba_label"].dropna().unique())

    # Set a default if the user has not picked one before
    if "admix_ancestry_choice" not in st.session_state:
        st.session_state["admix_ancestry_choice"] = "All"

    # Let the user select from our list of ancestries
    selected_ancestry = st.selectbox(
        label="Ancestry Selection",
        options=admix_ancestry_options,
        index=admix_ancestry_options.index(st.session_state["admix_ancestry_choice"])
        if st.session_state["admix_ancestry_choice"] in admix_ancestry_options
        else 0,
    )

    st.session_state["admix_ancestry_choice"] = selected_ancestry


def plot_pie(df: pd.DataFrame):
    """
    Interactive pie chart of ancestry proportions.
    """
    pie_chart = px.pie(
        df,
        names='Ancestry Category',
        values='Proportion',
        hover_name='Ancestry Category',
        color="Ancestry Category",
        color_discrete_map={
            'AFR': "#88CCEE",
            'SAS': "#CC6677",
            'EAS': "#DDCC77",
            'EUR': "#117733",
            'AMR': "#332288",
            'AJ':  "#D55E00",
            'AAC': "#999933",
            'CAS': "#882255",
            'MDE': "#661100",
            'FIN': "#F0E442",
            'CAH': "#40B0A6"
        }
    )
    pie_chart.update_layout(showlegend=True, width=500, height=500)
    st.plotly_chart(pie_chart)


class AncestryPage:
    def __init__(self):
        # Set page-wide config
        st.set_page_config(layout="wide")
        # Build the sidebar (this sets release_choice, cohort_choice, etc.)
        get_sidebar(self)

        st.title("🧬 Ancestry")

    def display(self):
        """
        Main entry point for rendering the Ancestry page.
        """
        gp2_data_bucket = st.session_state["gt_app_utils_bucket"]

        # Grab the full/unmodified master_key from session_state
        master_key_full = st.session_state["master_key"]

        # Filter locally (without overwriting the master key in session_state)
        master_key_filtered = filter_master_key(master_key_full)

        # If the user selects a specific cohort (other than FULL), subset the filtered DataFrame
        if (
            st.session_state["cohort_choice"]
            and not st.session_state["cohort_choice"].startswith("GP2 Release")
        ):
            master_key_filtered = master_key_filtered[
                master_key_filtered["study"] == st.session_state["cohort_choice"]
            ]

        # Remove pruned samples
        master_key_filtered["pruned"] = np.where(
            master_key_filtered.nba_prune_reason.isna(), 
            False, 
            True
        )
        master_key_filtered = master_key_filtered[master_key_filtered["pruned"] == 0]

        # Create tabs
        tabPCA, tabPredStats, tabPie, tabAdmix, tabMethods = st.tabs([
            "Ancestry Prediction",
            "Model Performance",
            "Ancestry Distribution",
            "Admixture Populations",
            "Method Description"
        ])

        # --------------------------------------------------------
        # Tab 1: PCA
        # --------------------------------------------------------
        with tabPCA:
            # No release_bucket reference. Use 'release_qc_path' instead:
            pca_folder = f'{st.session_state["release_qc_path"]}'

            # reference_pcs.csv, projected_pcs.csv are stored under that path in the same GCS bucket
            ref_pca = blob_as_csv(gp2_data_bucket, f'{pca_folder}/reference_pcs.csv', sep=',')
            proj_pca = blob_as_csv(gp2_data_bucket, f'{pca_folder}/projected_pcs.csv', sep=',')
            proj_pca = proj_pca.drop(columns=['label'], errors='ignore')

            # Merge with master_key to get final labels
            proj_pca_cohort = proj_pca.merge(
                master_key_filtered[['GP2ID', 'nba_label', 'study']], 
                how='inner', 
                left_on=['IID'], 
                right_on=['GP2ID']
            ).drop(columns=['GP2ID'], axis=1)
            
            proj_pca_cohort['plot_label'] = 'Predicted'
            ref_pca['plot_label'] = ref_pca['label']

            total_pca = pd.concat([ref_pca, proj_pca_cohort], axis=0)

            pca_col1, pca_col2 = st.columns([1.5, 3])
            st.markdown('---')
            col1, col2 = st.columns([1.5, 3])
            combined_labeled = (
                proj_pca_cohort[['IID', 'nba_label']]
                .rename(columns={'nba_label': 'Predicted Ancestry'})
            )
            st.dataframe(proj_pca)
            holdValues = combined_labeled['Predicted Ancestry'].value_counts().rename_axis(
                'Predicted Ancestry'
            ).reset_index(name='Counts')

            # Left column: table with "Select" ancestry
            with pca_col1:
                st.markdown(f'### Reference Panel vs. {st.session_state["cohort_choice"]} PCA')
                with st.expander("Description"):
                    st.write(
                        "Select an Ancestry Category below to display only those predicted samples "
                        "in the 3D PCA."
                    )

                holdValues['Select'] = False
                select_ancestry = st.data_editor(
                    holdValues, 
                    hide_index=True, 
                    use_container_width=True
                )
                selectionList = select_ancestry.loc[select_ancestry['Select'] == True]['Predicted Ancestry']

            # Right column: 3D PCA plot
            with pca_col2:
                if not selectionList.empty:
                    selected_pca = proj_pca_cohort.copy()
                
                    selected_pca.drop(
                        selected_pca[~selected_pca['nba_label'].isin(selectionList)].index,
                        inplace=True
                    )
                    # For selected categories, unify label to 'Predicted'
                    for item in selectionList:
                        selected_pca.replace({item: 'Predicted'}, inplace=True)
                    total_pca_selected = pd.concat([ref_pca, selected_pca], axis=0)
                    plot_3d(total_pca_selected, 'label')
                else:
                    plot_3d(total_pca, 'plot_label')

            with col1:
                st.markdown(f'### {st.session_state["cohort_choice"]} PCA')
                with st.expander("Description"):
                    st.write(
                        "All Predicted samples and their respective labels. "
                        "Use ⌘+F / Ctrl+F to search."
                    )
                st.dataframe(combined_labeled, hide_index=True, use_container_width=True)

            with col2:
                plot_3d(proj_pca_cohort, 'nba_label')

        # --------------------------------------------------------
        # Tab 2: Model Performance (Confusion Matrix)
        # --------------------------------------------------------
        with tabPredStats:
            st.markdown("## **Model Accuracy**")

            # Reuse your "release_qc_path"
            confusion_path = f'{st.session_state["release_qc_path"]}/confusion_matrix.csv'
            confusion_matrix = blob_as_csv(gp2_data_bucket, confusion_path, sep=',')

            if 'label' in confusion_matrix.columns:
                confusion_matrix.set_index('label', inplace=True)
            elif 'Unnamed: 0' in confusion_matrix.columns:
                confusion_matrix.rename({'Unnamed: 0': 'label'}, axis=1, inplace=True)
                confusion_matrix.set_index('label', inplace=True)

            tp = np.diag(confusion_matrix)
            col_sum = confusion_matrix.sum(axis=0)
            row_sum = confusion_matrix.sum(axis=1)

            class_recall = tp / row_sum
            class_precision = tp / col_sum

            balanced_accuracy = np.mean(class_recall)
            margin_of_error = 1.96 * np.sqrt(
                (balanced_accuracy * (1 - balanced_accuracy)) / sum(col_sum)
            )
            precision = np.mean(class_precision)
            f1 = np.mean(
                2 * ((class_recall * class_precision) / (class_recall + class_precision))
            )

            heatmap1, heatmap2 = st.columns([2, 1])
            with heatmap1:
                st.markdown("### Confusion Matrix")
                fig_cm = px.imshow(
                    confusion_matrix,
                    labels=dict(x="Predicted Ancestry", y="Reference Panel Ancestry", color="Count"),
                    text_auto=True,
                    color_continuous_scale="plasma",
                )
                fig_cm.update_layout(
                    plot_bgcolor='rgba(0, 0, 0, 0)', 
                    paper_bgcolor='rgba(0, 0, 0, 0)'
                )
                st.plotly_chart(fig_cm)

            with heatmap2:
                st.markdown("### Test Set Performance")
                st.markdown("#")
                st.metric(
                    "Balanced Accuracy:", 
                    f"{balanced_accuracy:.3f} ± {margin_of_error:.3f}"
                )
                st.markdown("#")
                st.metric("Precision:", f"{precision:.3f}")
                st.markdown("#")
                st.metric("F1 Score:", f"{f1:.3f}")

        # --------------------------------------------------------
        # Tab 3: Ancestry Distribution (Pie Charts)
        # --------------------------------------------------------
        with tabPie:
            # If reference PCA is also in meta_data/qc_metrics
            ref_pca_path = f'{st.session_state["release_qc_path"]}/reference_pcs.csv'
            ref_pca = blob_as_csv(gp2_data_bucket, ref_pca_path, sep=',')

            # Reference panel
            df_ref_prop = (
                ref_pca['label']
                .value_counts(normalize=True)
                .rename_axis('Ancestry Category')
                .reset_index(name='Proportion')
            )
            ref_counts = (
                ref_pca['label']
                .value_counts()
                .rename_axis('Ancestry Category')
                .reset_index(name='Counts')
            )
            ref_merged = pd.merge(df_ref_prop, ref_counts, on='Ancestry Category')
            ref_merged.rename(
                columns={'Proportion': 'Ref Panel Proportion', 'Counts': 'Ref Panel Counts'},
                inplace=True
            )

            # Predicted panel
            df_pred_prop = (
                master_key_filtered['nba_label']
                .value_counts(normalize=True)
                .rename_axis('Ancestry Category')
                .reset_index(name='Proportion')
            )
            pred_counts = (
                master_key_filtered['nba_label']
                .value_counts()
                .rename_axis('Ancestry Category')
                .reset_index(name='Counts')
            )
            pred_merged = pd.merge(df_pred_prop, pred_counts, on='Ancestry Category')
            pred_merged.rename(
                columns={'Proportion': 'Predicted Proportion', 'Counts': 'Predicted Counts'},
                inplace=True
            )

            ref_combo = ref_merged[['Ancestry Category', 'Ref Panel Counts']]
            # Ensure CAH is present
            cah_row = pd.DataFrame([['CAH', 'NA']], columns=['Ancestry Category', 'Ref Panel Counts'])
            ref_combo = pd.concat([ref_combo, cah_row], axis=0)

            pie_table = pd.merge(ref_combo, pred_merged, on='Ancestry Category', how='outer')
            pie_table.fillna(0, inplace=True)

            pie1, _, pie3 = st.columns([2, 1, 2])
            _, p2, _ = st.columns([2, 4, 2])

            with pie1:
                st.markdown("### **Reference Panel Ancestry**")
                plot_pie(df_ref_prop)

            with pie3:
                st.markdown(f"### {st.session_state['cohort_choice']} Predicted Ancestry")
                plot_pie(df_pred_prop)

            with p2:
                st.dataframe(
                    pie_table[
                        ['Ancestry Category', 'Ref Panel Counts', 'Predicted Counts']
                    ],
                    hide_index=True,
                    use_container_width=True
                )

        # --------------------------------------------------------
        # Tab 4: Admixture
        # --------------------------------------------------------
        with tabAdmix:
            frontend_bucket = get_gcloud_bucket('gt_app_utils')
            st.markdown("## **Reference Panel Admixture Populations**")

            with st.expander("Description"):
                st.write(
                    "Results of running ADMIXTURE on the reference panel with K=10. "
                    "Use the selector to subset the admixture table by ancestry."
                )

            # Typically stored under 'ref_panel_admixture.txt' in same or separate bucket
            ref_admix = blob_as_csv(frontend_bucket, 'ref_panel_admixture.txt')

            # If you have an image saved in that same bucket:
            admix_plot_blob = frontend_bucket.get_blob('refpanel_admix.png')
            if admix_plot_blob:
                admix_plot = admix_plot_blob.download_as_bytes()
                st.image(admix_plot)

            # Let user pick an ancestry
            admix_ancestry_select()
            admix_ancestry_choice = st.session_state['admix_ancestry_choice']

            if admix_ancestry_choice != 'All':
                ref_admix = ref_admix[ref_admix['ancestry'] == admix_ancestry_choice]

            st.dataframe(ref_admix, hide_index=True, use_container_width=True)

        # --------------------------------------------------------
        # Tab 5: Method Description
        # --------------------------------------------------------
        with tabMethods:
            st.markdown("## _Ancestry_")
            st.markdown("### _Reference Panel_")
            st.markdown(
                "The reference panel is composed of 4008 samples from 1000 Genomes Project, "
                "Human Genome Diversity Project (HGDP), and an Ashkenazi Jewish reference panel "
                "(GEO accession no. GSE23636), with the following ancestral makeup:"
            )
            st.markdown(
                """
                - African (AFR): 819  
                - African Admixed and Caribbean (AAC): 74  
                - Ashkenazi Jewish (AJ): 471  
                - Central Asian (CAS): 183  
                - East Asian (EAS): 585  
                - European (EUR): 534  
                - Finnish (FIN): 99  
                - Latino/American Admixed (AMR): 490  
                - Middle Eastern (MDE): 152  
                - South Asian (SAS): 601
                """
            )
            st.markdown(
                "Samples were chosen from 1000 Genomes and HGDP to match the specific ancestries in GP2. "
                "The reference panel was pruned for palindrome SNPs and for maf 0.05, geno 0.01, and hwe 0.0001."
            )

            st.markdown("### _Preprocessing_")
            st.markdown(
                "Genotypes were pruned for geno 0.1. Common variants between the reference panel and the genotypes "
                "were extracted. Any missing genotypes were imputed by the mean of that variant in the reference panel. "
                "The reference panel was split into an 80/20 train/test set. PCA was run using sklearn, etc."
            )

            st.markdown("### _UMAP + Classifier Training_")
            st.markdown(
                "A classifier was trained using UMAP transformations of the PCs and a linear XGBoost classifier "
                "with 5-fold cross-validation. We gridsearched over parameters like:"
            )
            st.markdown(
                """
                - "umap__n_neighbors": [5,20]  
                - "umap__n_components": [15,25]  
                - "umap__a": [0.75, 1.0, 1.5]  
                - "umap__b": [0.25, 0.5, 0.75]  
                - "xgboost__lambda": [0.001, 0.01, 0.1, 1, 10, 100]
                """
            )
            st.markdown(
                "Performance is ~95-98% balanced accuracy on the test set."
            )

            st.markdown("### _Prediction_")
            st.markdown(
                "Scaled PCs are transformed using the training set UMAP, then predicted by the trained classifier. "
                "Prior to release 5, AFR and AAC labels were separated by an ADMIXTURE threshold. From release 5 onward, "
                "a perceptron model refines reference panel labels, approximating the previous ADMIXTURE approach."
            )

            st.markdown("### _Complex Admixture History_")
            st.markdown(
                "Highly admixed samples not well-represented by the reference panel are labeled 'CAH'. "
                "Because no reference samples exist for CAH, a PC-based approach finds any sample closer "
                "to the overall centroid than to any reference ancestry centroid, labeling it 'CAH'."
            )


# If you'd like to run this page standalone:
if __name__ == "__main__":
    page = AncestryPage()
    page.display()

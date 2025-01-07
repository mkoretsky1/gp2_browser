import streamlit as st
import pandas as pd
import plotly.express as px
from utils.utils import (
    MetadataPlotter,
    MetadataProcessor,
    get_sidebar,
    filter_master_key,
)
from utils.state import initialize_state


class MetadataPage:
    def __init__(self):
        st.set_page_config(layout="wide")
        initialize_state()
        get_sidebar(self)

        self.metadata_plotter = MetadataPlotter()
        self.metadata_processor = MetadataProcessor()

        st.title("🧬 Metadata")

    def display(self):
        master_key = filter_master_key(st.session_state["master_key"])
        phenotype_column = "baseline_GP2_phenotype_for_qc"

        plot1, plot2 = st.columns([1, 1.75])
    
        master_key = master_key.loc[master_key.biological_sex_for_qc!='Other/Unknown/Not Reported']
        if master_key.shape[0] != 0:
            plot1.markdown("#### Stratify Age by:")
            stratify = plot1.radio(
                "Stratify Age by:",
                ("None", "Sex", "Phenotype"),
                label_visibility="collapsed",
            )

            if not "age_at_sample_collection" in master_key.columns:
                plot2.error("Error: 'age_at_sample_collection' column not found in the DataFrame.")
            
            elif stratify == "Sex" and not "biological_sex_for_qc" in master_key.columns:
                plot2.error("Error: 'biological_sex_for_qc' column not found in the DataFrame. Cannot stratify by Sex.")
            
            elif stratify == "Phenotype" and not phenotype_column in master_key.columns:
                plot2.error(f"Error: '{phenotype_column}' column not found in the DataFrame. Cannot stratify by Phenotype.")

            else:
                if stratify == "None":
                    fig = px.histogram(
                        master_key,
                        x="age_at_sample_collection",
                        nbins=25,
                        color_discrete_sequence=["#332288"],
                        labels={
                            "age_at_sample_collection": "Age at Sample Collection"
                        },
                    )
                    fig.update_layout(
                        title_text=f"<b>Age Distribution<b>",
                        xaxis_title="Age at Sample Collection",
                        yaxis_title="Count",
                        bargap=0.1,
                        autosize=True
                    )
                    plot2.plotly_chart(fig, use_container_width=True)
                else:
                    if stratify == "Sex":
                        color_column = "biological_sex_for_qc"
                        color_map = {"Male": "#332288", "Female": "#CC6677", "Other": "purple"}
                        labels = {"age_at_sample_collection": "Age at Sample Collection", "biological_sex_for_qc": "Sex"}
                        title = "<b>Age Distribution by Sex<b>"
                    else: # stratify == "Phenotype"
                        color_column = phenotype_column
                        color_map = None
                        labels = {"age_at_sample_collection": "Age at Sample Collection", phenotype_column: "Phenotype"}
                        title = "<b>Age Distribution by Phenotype<b>"

                    fig = px.histogram(
                        master_key,
                        x="age_at_sample_collection",
                        color=color_column,
                        nbins=25,
                        color_discrete_map=color_map,
                        labels=labels
                    )
                    
                    unique_count = len(master_key[color_column].dropna().unique())

                    fig.update_layout(
                        title_text=title,
                        xaxis_title="Age at Sample Collection",
                        yaxis_title="Count",
                        bargap=0.1,
                        autosize=True
                    )
                    plot2.plotly_chart(fig, use_container_width=True)

            plot1.markdown("---")

        master_key['biological_sex_for_qc'] = master_key['biological_sex_for_qc'].replace('Unknown', 'Other')
        male_pheno = master_key.loc[
            master_key["biological_sex_for_qc"] == "Male", phenotype_column
        ]
        female_pheno = master_key.loc[
            master_key["biological_sex_for_qc"] == "Female", phenotype_column
        ]

        combined_counts = pd.DataFrame()
        combined_counts["Male"] = male_pheno.value_counts()
        combined_counts["Female"] = female_pheno.value_counts()
        combined_counts = combined_counts.transpose()
        combined_counts["Total"] = combined_counts.sum(axis=1)
        combined_counts = combined_counts.fillna(0)
        combined_counts = combined_counts.astype("int32")

        plot1.markdown("#### Phenotype Count Split by Sex")
        plot1.dataframe(combined_counts, use_container_width=True)


if __name__ == "__main__":
    page = MetadataPage()
    page.display()
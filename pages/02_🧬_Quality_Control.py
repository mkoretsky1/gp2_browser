import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from functools import reduce
from dataclasses import dataclass
from utils.utils import get_sidebar, filter_master_key, blob_as_csv
from utils.state import initialize_state


@dataclass
class QCPlotter:
    def create_funnel_plot(self, funnel_df: pd.DataFrame) -> go.Figure:
        """Create a funnel plot showing the sample filtering steps."""
        fig = go.Figure(go.Funnelarea(
            text=[f'<b>{i}</b>' for i in funnel_df['step_name']],
            values=funnel_df['remaining_samples'],
            marker={"colors": ["#999999", "#E69F00", "#56B4E9", "#009E73", "#AA4499", 
                             "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]},
            opacity=1.0,
            textinfo='text',
            customdata=funnel_df['remaining_samples'],
            hovertemplate='Remaining Samples:<br>%{customdata[0]:.f}<extra></extra>'
        ))
        fig.update_layout(showlegend=False, margin=dict(l=0, r=300, t=10, b=0))
        return fig

    def create_relatedness_plot(self, df_relatedness: pd.DataFrame) -> go.Figure:
        """Create a horizontal bar plot showing relatedness per ancestry."""
        fig = go.Figure(data=[
            go.Bar(y=df_relatedness.nba_label, x=df_relatedness['related_count'],
                  orientation='h', name="Related", base=0, marker_color="#0072B2"),
            go.Bar(y=df_relatedness.nba_label, x=-df_relatedness['duplicated_count'],
                  orientation='h', name="Duplicated", base=0, marker_color="#D55E00")
        ])
        
        fig.update_layout(
            barmode='stack',
            autosize=False,
            height=500,
            width=750,
            margin=dict(l=0, r=200, t=10, b=60),
            yaxis=dict(
                ticktext=df_relatedness.nba_label,
                tickvals=df_relatedness.nba_label
            )
        )
        return fig

    def create_variant_filtering_plot(self, df_merged: pd.DataFrame) -> go.Figure:
        """Create a stacked bar plot showing variant filtering per ancestry."""
        fig = go.Figure()
        
        colors = {
            'geno_removed_count': "#0072B2",
            'mis_removed_count': "#882255",
            'haplotype_removed_count': "#44AA99",
            'hwe_removed_count': "#D55E00"
        }
        
        for col, color in colors.items():
            fig.add_trace(go.Bar(
                x=df_merged.index,
                y=df_merged[col],
                name=' '.join(col.split('_')).title(),
                marker_color=color
            ))

        fig.update_layout(
            xaxis=dict(
                categoryorder='total descending',
                title='Ancestry',
                tickfont_size=14
            ),
            yaxis=dict(
                title='Count',
                titlefont_size=16,
                tickfont_size=14
            ),
            barmode='stack',
            width=1100,
            height=600
        )
        return fig


@dataclass
class QCProcessor:
    def process_variant_filtering(self, df_qc: pd.DataFrame) -> pd.DataFrame:
        """Process variant filtering data."""
        if int(st.session_state['release_choice']) >= 6:
            df = df_qc
        else:
            df = df_qc.query("step == 'variant_prune'")
            
        df = df[['ancestry', 'pruned_count', 'metric']]

        metrics = {
            'geno_removed_count': df.query("metric == 'geno_removed_count'"),
            'mis_removed_count': df.query("metric == 'mis_removed_count'"),
            'haplotype_removed_count': df.query("metric == 'haplotype_removed_count'"),
            'hwe_removed_count': df.query("metric == 'hwe_removed_count'"),
            'total_removed_count': df.query("metric == 'total_removed_count'")
        }
        
        dfs = []
        for metric_name, metric_df in metrics.items():
            if not metric_df.empty:
                df_processed = metric_df.copy()
                df_processed = df_processed.rename(columns={'pruned_count': metric_name})
                df_processed = df_processed.drop(columns=['metric'])
                dfs.append(df_processed)

        df_merged = reduce(lambda left, right: pd.merge(left, right, on=['ancestry'], how='outer'), dfs)
        df_merged.set_index('ancestry', inplace=True)
        return df_merged

    def process_pruning_steps(self, master_key: pd.DataFrame) -> pd.DataFrame:
        """Process and create pruning steps dataframe."""
        pre_QC_total = master_key['GP2ID'].count()
        funnel_df = pd.DataFrame(columns=['remaining_samples', 'step'])
        funnel_df.loc[0] = pd.Series({'remaining_samples': pre_QC_total, 'step': 'pre_QC'})

        hold_prunes = master_key['nba_prune_reason'].value_counts().reset_index()
        hold_prunes.columns = ['nba_prune_reason', 'pruned_counts']
        remaining_samples = pre_QC_total

        ordered_prune = ['insufficient_ancestry_sample_n', 'phenotype_not_reported',
                        'missing_idat', 'missing_bed', 'callrate_prune', 'sex_prune',
                        'het_prune', 'duplicated_prune']

        steps_dict = {
            'pre_QC': 'Pre-QC',
            'insufficient_ancestry_sample_n': 'Insufficient Ancestry Count',
            'missing_idat': 'Missing IDAT',
            'missing_bed': 'Missing BED',
            'phenotype_not_reported': 'Phenotype Not Reported',
            'callrate_prune': 'Call Rate Prune',
            'sex_prune': 'Sex Prune',
            'duplicated_prune': 'Duplicated',
            'het_prune': 'Heterozygosity Prune'
        }

        for prune in ordered_prune:
            obs_pruned = hold_prunes['nba_prune_reason'].tolist()
            if prune not in obs_pruned:
                remaining_samples -= 0
            else:
                row = hold_prunes.loc[hold_prunes['nba_prune_reason'] == prune]
                remaining_samples -= row.iloc[0]['pruned_counts']
            funnel_df.loc[len(funnel_df.index)] = pd.Series({
                'remaining_samples': remaining_samples,
                'step': prune
            })

        funnel_df['step_name'] = funnel_df['step'].map(steps_dict)
        return funnel_df

    def process_relatedness(self, master_key: pd.DataFrame, ancestry_dict: dict,
                          ancestry_index: dict) -> pd.DataFrame:
        """Process and create relatedness dataframe."""
        df_related = master_key[
            (master_key['nba_related'] == 1) | 
            (master_key['nba_prune_reason'] == 'duplicated_prune')
        ][['nba_label', 'pruned']]

        df_relatedness = []
        for label in ancestry_dict:
            ancestry_data = {
                'ancestry': label,
                'related_count': 0,
                'duplicated_count': 0
            }
            
            if label in df_related['nba_label'].unique():
                df_ancestry = df_related[df_related['nba_label'] == label]
                ancestry_data.update({
                    'related_count': df_ancestry[df_ancestry['pruned'] == 0].shape[0],
                    'duplicated_count': df_ancestry[df_ancestry['pruned'] == 1].shape[0]
                })
            
            df_relatedness.append(ancestry_data)

        df_relatedness = pd.DataFrame(df_relatedness)
        df_relatedness['nba_label'] = df_relatedness['ancestry'].map(ancestry_dict)
        df_relatedness['label_index'] = df_relatedness['ancestry'].map(ancestry_index)
        df_relatedness = df_relatedness.sort_values(by=['label_index'], ascending=True)
        df_relatedness.set_index('ancestry', inplace=True)
        
        return df_relatedness


class QualityControlPage:
    def __init__(self):
        st.set_page_config(layout="wide")
        initialize_state()
        get_sidebar(self)
        
        self.qc_plotter = QCPlotter()
        self.qc_processor = QCProcessor()
        
        st.title("🧬 Quality Control")
        st.title(f'{st.session_state["cohort_choice"]} Metrics')

    def load_qc_data(self) -> pd.DataFrame:
        """Load QC metrics data."""
        return blob_as_csv(st.session_state["gt_app_utils_bucket"], 
                  f'{st.session_state["release_qc_path"]}/qc_metrics.csv')

    def get_ancestry_mappings(self) -> tuple:
        """Get ancestry dictionaries based on release version."""
        ancestry_dict = {
            'AFR': 'African', 'SAS': 'South Asian', 'EAS': 'East Asian',
            'EUR': 'European', 'AMR': 'American', 'AJ': 'Ashkenazi Jewish',
            'AAC': 'African American/Afro-Caribbean', 'CAS': 'Central Asian',
            'MDE': 'Middle Eastern', 'FIN': 'Finnish', 'CAH': 'Complex Admixture History'
        }
        
        ancestry_index = {
            'AFR': 3, 'SAS': 7, 'EAS': 8, 'EUR': 0, 'AMR': 2, 'AJ': 1,
            'AAC': 4, 'CAS': 5, 'MDE': 6, 'FIN': 9, 'CAH': 10
        }

        release_choice = st.session_state['release_choice']
        if int(release_choice) < 3:
            for key in ['CAS', 'MDE']:
                ancestry_dict.pop(key)
                ancestry_index.pop(key)

        if int(release_choice) < 6:
            ancestry_dict.pop('CAH')
            ancestry_index.pop('CAH')

        return ancestry_dict, ancestry_index

    def display(self):
        master_key = filter_master_key(st.session_state["master_key"])
        master_key.loc[:,'pruned'] = np.where(master_key.nba_prune_reason.isna(), False, True)
        ancestry_dict, ancestry_index = self.get_ancestry_mappings()

        st.header('QC Step 1: Sample-Level Filtering')
        with st.expander("Description", expanded=False):
            st.markdown(
                'Genotypes are pruned for call rate with maximum sample genotype '
                'missingness of 0.02 (--mind 0.02). Samples which pass call rate pruning '
                'are then pruned for discordant sex where samples with 0.25 <= sex F <= '
                '0.75 are pruned. Sex F < 0.25 are female and Sex F > 0.75 are male. '
                'Samples that pass sex pruning are then differentiated by ancestry. '
                'Per-ancestry genotypes are then pruned for genetic relatedness using '
                'KING, where a cutoff of 0.0884 was used to determine second degree '
                'relatedness and 0.354 is used to determine duplicates.'
            )

        left_col1, right_col1 = st.columns([1.5, 2])

        funnel_df = self.qc_processor.process_pruning_steps(master_key)
        with left_col1:
            st.header("**All Sample Filtering Counts**")
            funnel_plot = self.qc_plotter.create_funnel_plot(funnel_df)
            st.plotly_chart(funnel_plot)

        df_relatedness = self.qc_processor.process_relatedness(
            master_key, ancestry_dict, ancestry_index
        )
        if len(df_relatedness) > 0:
            with right_col1:
                st.header("**Relatedness per Ancestry**")
                relatedness_plot = self.qc_plotter.create_relatedness_plot(df_relatedness)
                st.plotly_chart(relatedness_plot)

        st.markdown('---')
        
        # Variant filtering section
        st.header('QC Step 2: Variant-Level Filtering')
        with st.expander("Description", expanded=False):
            st.markdown(
                'Variants are pruned for missingness by case-control where P<=1e-4 to '
                'detect platform/batch differences in case-control status. Next, variants '
                'are pruned for missingness by haplotype for flanking variants where '
                'P<=1e-4. Lastly, controls are filtered for HWE at a threshold of 1e-4. '
                'Please note that for each release, variant pruning is performed in an '
                'ancestry-specific manner, and thus the numbers in the bar chart below '
                'will not change based on cohort selection within the same release.'
            )

        # Load and process QC metrics data
        df_qc = self.load_qc_data()
        df_merged = self.qc_processor.process_variant_filtering(df_qc)
        
        st.header("**Variant Filtering per Ancestry**")
        variant_plot = self.qc_plotter.create_variant_filtering_plot(df_merged)
        st.plotly_chart(variant_plot)
        
        st.markdown('---')
        
        # Display failed prune steps if any exist
        df_failed = df_qc[df_qc['pass'] == False].reset_index(drop=True)
        if not df_failed.empty:
            st.markdown("**Failed Prune Steps**")
            failed_prune_exp = st.expander("Description", expanded=False)
            with failed_prune_exp:
                st.write(
                    'Prune step considered "failed" if there was an insufficient number '
                    'of samples within an ancestry to complete the step, even if no '
                    'samples were pruned.'
                )
            
            hide_table_row_index = """
                <style>
                    thead tr th:first-child {display:none}
                    tbody th {display:none}
                </style>
            """
            st.markdown(hide_table_row_index, unsafe_allow_html=True)
            st.table(df_failed)


if __name__ == "__main__":
    page = QualityControlPage()
    page.display()
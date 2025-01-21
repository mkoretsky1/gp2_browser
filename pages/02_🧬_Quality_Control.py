import streamlit as st
from utils.hold_data import (
    release_select, 
    config_page
)
from utils.quality_control_utils import (
    load_qc_data,
    prepare_funnel_data,
    prepare_relatedness_data,
    prepare_variant_data,
    create_qc_plots
)


def main():
    
    config_page('Quality Control')
    release_select()

    master_key, df_qc = load_qc_data()

    funnel_df = prepare_funnel_data(master_key)
    ancestry_dict = {
        'AFR': 'African', 
        'SAS': 'South Asian', 
        'EAS': 'East Asian', 
        'EUR': 'European',
        'AMR': 'American', 
        'AJ': 'Ashkenazi Jewish', 
        'AAC': 'African American/Afro-Caribbean',
        'CAS': 'Central Asian', 
        'MDE': 'Middle Eastern', 
        'FIN': 'Finnish', 
        'CAH': 'Complex Admixture History'
    }

    ancestry_index = {
        'AFR': 3,
        'SAS': 7, 
        'EAS': 8, 
        'EUR': 0, 
        'AMR': 2, 
        'AJ': 1,
        'AAC': 4, 
        'CAS': 5, 
        'MDE': 6, 
        'FIN': 9, 
        'CAH': 10
    }

    relatedness_df = prepare_relatedness_data(master_key, ancestry_dict, ancestry_index)
    variant_df = prepare_variant_data(df_qc)

    funnel_plot, relatedness_plot, variant_plot = create_qc_plots(funnel_df, relatedness_df, variant_df)

    st.title(f"{st.session_state['cohort_choice']} Metrics")

    st.header('QC Step 1: Sample-Level Filtering')
    with st.expander("Description", expanded=False):
        st.markdown('Sample-level pruning process description here.')

    left_col1, right_col1 = st.columns(2)

    with left_col1:
        st.header("**All Sample Filtering Counts**")
        st.plotly_chart(funnel_plot, use_container_width=True)

    with right_col1:
        if not relatedness_df.empty:
            st.header("**Relatedness per Ancestry**")
            st.plotly_chart(relatedness_plot, use_container_width=True)

    st.header('QC Step 2: Variant-Level Filtering')
    with st.expander("Description", expanded=False):
        st.markdown('Variant-level pruning process description here.')

    st.plotly_chart(variant_plot)

if __name__ == "__main__":
    main()

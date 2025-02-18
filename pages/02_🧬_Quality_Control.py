import streamlit as st
from utils.hold_data import (
    release_select, 
    config_page
)
from utils.quality_control_utils import (
    load_qc_data,
    create_qc_plots
)
from utils.config import AppConfig

config = AppConfig()

def main():
    
    config_page('Quality Control')
    release_select()

    funnel_df, related_df, variant_df = load_qc_data()
    funnel_plot, relatedness_plot, variant_plot = create_qc_plots(funnel_df, related_df, variant_df)

    st.title(f"Release {st.session_state['release_choice']} Metrics")

    st.header('QC Step 1: Sample-Level Filtering')
    with st.expander("Description", expanded=False):
        st.markdown(config.DESCRIPTIONS['qc'])

    left_col1, right_col1 = st.columns([1.5,2])

    with left_col1:
        st.header("**All Sample Filtering Counts**")
        st.plotly_chart(funnel_plot, use_container_width=True)

    with right_col1:
        if not related_df.empty:
            st.header("**Relatedness per Ancestry**")
            st.plotly_chart(relatedness_plot, use_container_width=True)
            # st.dataframe(related_df[['label', 'related_count', 'duplicated_count']], use_container_width = True, height = 423)

    st.header('QC Step 2: Variant-Level Filtering')
    with st.expander("Description", expanded=False):
        st.markdown(config.DESCRIPTIONS['variant'])

    st.plotly_chart(variant_plot, use_container_width = True)

if __name__ == "__main__":
    main()

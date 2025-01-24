import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from utils.hold_data import (
    blob_as_csv,
    get_gcloud_bucket,
    admix_ancestry_select
)
from utils.config import AppConfig

config = AppConfig()

def plot_3d(labeled_df, color, symbol=None, x='PC1', y='PC2', z='PC3', title=None, x_range=None, y_range=None, z_range=None):
    """
    Create a 3D scatter plot using Plotly.

    Parameters:
        labeled_df (pd.DataFrame): Input dataframe containing PCA components and labels.
        color (str): Column name containing labels for ancestry.
        symbol (str, optional): Secondary label (e.g., predicted vs reference ancestry).
        x (str, optional): Column name of the x-dimension. Defaults to 'PC1'.
        y (str, optional): Column name of the y-dimension. Defaults to 'PC2'.
        z (str, optional): Column name of the z-dimension. Defaults to 'PC3'.
        title (str, optional): Plot title.
        x_range (list of float, optional): Range for x-axis [min, max].
        y_range (list of float, optional): Range for y-axis [min, max].
        z_range (list of float, optional): Range for z-axis [min, max].
    """
    fig = px.scatter_3d(
        labeled_df,
        x=x,
        y=y,
        z=z,
        color=color,
        symbol=symbol,
        title=title,
        color_discrete_map=config.ANCESTRY_COLOR_MAP,
        color_discrete_sequence=px.colors.qualitative.Bold,
        range_x=x_range,
        range_y=y_range,
        range_z=z_range,
        hover_name="IID"
    )
    fig.update_traces(marker={'size': 3})
    st.plotly_chart(fig)

def plot_confusion_matrix(confusion_matrix):
    """
    Plot the given confusion matrix.

    Parameters:
        confusion_matrix (pd.DataFrame): Confusion matrix with reference ancestry as rows
        and predicted ancestry as columns.
    """
    fig = px.imshow(
        confusion_matrix,
        labels=dict(x="Predicted Ancestry", y="Reference Panel Ancestry", color="Count"),
        text_auto=True,
        color_continuous_scale='viridis'
    )
    fig.update_layout(
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)'
    )
    fig.update_yaxes(title_font_color="black", tickfont=dict(color='black'))
    fig.update_xaxes(title_font_color="black", tickfont=dict(color='black'))
    st.plotly_chart(fig)

def plot_pie(df):
    """
    Create an interactive pie chart using Plotly.

    Parameters:
        df (pd.DataFrame): Dataframe with columns ['Ancestry Category', 'Proportion'].
    """
    pie_chart = px.pie(
        df,
        names='Ancestry Category',
        values='Proportion',
        hover_name='Ancestry Category',
        color='Ancestry Category',
        color_discrete_map=config.ANCESTRY_COLOR_MAP
    )
    pie_chart.update_layout(showlegend=True, width=500, height=500)
    st.plotly_chart(pie_chart)


def render_tab_pca(pca_folder, gp2_data_bucket, master_key):
    """
    Render the PCA tab in the Streamlit interface.

    Parameters:
        pca_folder (str): Path to the folder containing PCA data.
        gp2_data_bucket (google.cloud.storage.bucket.Bucket): GCloud bucket object.
        master_key (pd.DataFrame): Master key dataframe.
    """
    ref_pca = blob_as_csv(gp2_data_bucket, f'{pca_folder}/reference_pcs.csv', sep=',')
    proj_pca = blob_as_csv(gp2_data_bucket, f'{pca_folder}/projected_pcs.csv', sep=',')
    proj_pca = proj_pca.drop(columns=['label'], axis=1)

    proj_pca_cohort = proj_pca.merge(
        master_key[['GP2sampleID', 'label', 'study']],
        how='inner',
        left_on=['IID'],
        right_on=['GP2sampleID']
    )
    proj_pca_cohort = proj_pca_cohort.drop(columns=['GP2sampleID'], axis=1)
    proj_pca_cohort['plot_label'] = 'Predicted'
    ref_pca['plot_label'] = ref_pca['label']

    total_pca = pd.concat([ref_pca, proj_pca_cohort], axis=0)
    new_labels = proj_pca_cohort['label']

    pca_col1, pca_col2 = st.columns([1.5, 3])
    st.markdown('---')
    col1, col2 = st.columns([1.5, 3])

    combined = proj_pca_cohort[['IID', 'label']]
    combined_labelled = combined.rename(columns={'label': 'Predicted Ancestry'})
    hold_values = combined['label'].value_counts().rename_axis('Predicted Ancestry').reset_index(name='Counts')

    with pca_col1:
        st.markdown(f'### Reference Panel vs. {st.session_state["cohort_choice"]} PCA')
        with st.expander("Description"):
            st.write(config.DESCRIPTIONS['pca1'])

        hold_values['Select'] = False
        select_ancestry = st.data_editor(hold_values, hide_index=True, use_container_width=True)
        selection_list = select_ancestry.loc[select_ancestry['Select'] == True]['Predicted Ancestry']

    with pca_col2:
        if not selection_list.empty:
            selected_pca = proj_pca_cohort.copy()
            selected_pca.drop(
                selected_pca[~selected_pca['label'].isin(selection_list)].index,
                inplace=True
            )
            for items in selection_list:
                selected_pca.replace({items: 'Predicted'}, inplace=True)
            total_pca_selected = pd.concat([ref_pca, selected_pca], axis=0)
            plot_3d(total_pca_selected, 'label')
        else:
            plot_3d(total_pca, 'plot_label')

    with col1:
        st.markdown(f'### {st.session_state["cohort_choice"]} PCA')
        with st.expander("Description"):
            st.write(config.DESCRIPTIONS['pca2'])
        st.dataframe(combined_labelled, hide_index=True, use_container_width=True)

    with col2:
        plot_3d(proj_pca_cohort, 'label')


def plot_confusion_matrix(confusion_matrix):
    """
    Plot the given confusion matrix as percentages rather than raw counts,
    using a color scale that looks good in both light and dark mode.

    Parameters:
        confusion_matrix (pd.DataFrame): Confusion matrix with reference ancestry as rows
                                         and predicted ancestry as columns.

    Returns:
        fig (plotly.graph_objs._figure.Figure): The Plotly figure object.
    """
    # Convert raw counts to row-based percentages
    confusion_matrix_percent = confusion_matrix.div(confusion_matrix.sum(axis=1), axis=0) * 100

    fig = px.imshow(
        confusion_matrix_percent.round(1),  # Round to one decimal place for cleaner display
        labels=dict(x="Predicted Ancestry", y="Reference Panel Ancestry", color="Percentage"),
        text_auto=".1f",  # Format text with one decimal place
        color_continuous_scale='Mint'
    )
    fig.update_layout(
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)'
    )
    fig.update_yaxes(title_font_color="white", tickfont=dict(color='white'))
    fig.update_xaxes(title_font_color="white", tickfont=dict(color='white'))

    return fig


def render_tab_pred_stats(pca_folder, gp2_data_bucket):
    """
    Render the Model Performance tab containing confusion matrix and performance metrics.

    Parameters:
        pca_folder (str): Path to the folder containing PCA data.
        gp2_data_bucket (google.cloud.storage.bucket.Bucket): GCloud bucket object.
    """
    st.markdown('## **Model Accuracy**')
    confusion_matrix = blob_as_csv(gp2_data_bucket, f'{pca_folder}/confusion_matrix.csv', sep=',')

    if 'label' in confusion_matrix.columns:
        confusion_matrix.set_index('label', inplace=True)
    elif 'Unnamed: 0' in confusion_matrix.columns:
        confusion_matrix = confusion_matrix.rename({'Unnamed: 0': 'label'}, axis=1)
        confusion_matrix.set_index('label', inplace=True)
    else:
        confusion_matrix.set_index(confusion_matrix.columns, inplace=True)

    tp = np.diag(confusion_matrix)
    col_sum = confusion_matrix.sum(axis=0)
    row_sum = confusion_matrix.sum(axis=1)

    class_recall = np.array(tp / row_sum)
    class_precision = np.array(tp / col_sum)

    balanced_accuracy = np.mean(class_recall)
    margin_of_error = 1.96 * np.sqrt(
        (balanced_accuracy * (1 - balanced_accuracy)) / sum(col_sum)
    )
    precision = np.mean(class_precision)
    f1 = np.mean(2 * ((class_recall * class_precision) / (class_recall + class_precision)))

    heatmap1, heatmap2 = st.columns([2, 1])
    with heatmap1:
        st.markdown('### Confusion Matrix')
        fig = plot_confusion_matrix(confusion_matrix)
        st.plotly_chart(fig)

    with heatmap2:
        st.markdown('### Test Set Performance')
        st.metric('Balanced Accuracy:', f"{balanced_accuracy:.3f} \u00B1 {margin_of_error:.3f}")
        st.metric('Precision:', f"{precision:.3f}")
        st.metric('F1 Score:', f"{f1:.3f}")


def render_tab_pie(pca_folder, gp2_data_bucket):
    """
    Render the Ancestry Distribution tab with reference and predicted pie charts.

    Parameters:
        pca_folder (str): Path to the folder containing PCA data.
        gp2_data_bucket (google.cloud.storage.bucket.Bucket): GCloud bucket object.
    """
    pie1, _, pie3 = st.columns([2, 1, 2])

    ref_pca = blob_as_csv(gp2_data_bucket, f'{pca_folder}/reference_pcs.csv', sep=',')
    df_ref_ancestry_counts = ref_pca['label'].value_counts(normalize=True).rename_axis('Ancestry Category').reset_index(name='Proportion')
    ref_counts = ref_pca['label'].value_counts().rename_axis('Ancestry Category').reset_index(name='Counts')
    ref_combo = pd.merge(df_ref_ancestry_counts, ref_counts, on='Ancestry Category')
    ref_combo.rename(columns={'Proportion': 'Ref Panel Proportion', 'Counts': 'Ref Panel Counts'}, inplace=True)

    df_pred_ancestry_counts = st.session_state['master_key']['label'].value_counts(normalize=True).rename_axis('Ancestry Category').reset_index(name='Proportion')
    pred_counts = st.session_state['master_key']['label'].value_counts().rename_axis('Ancestry Category').reset_index(name='Counts')
    pred_combo = pd.merge(df_pred_ancestry_counts, pred_counts, on='Ancestry Category')
    pred_combo.rename(columns={'Proportion': 'Predicted Proportion', 'Counts': 'Predicted Counts'}, inplace=True)

    ref_combo = ref_combo[['Ancestry Category', 'Ref Panel Counts']]
    ref_combo_cah = pd.DataFrame([['CAH', 'NA']], columns=['Ancestry Category', 'Ref Panel Counts'])
    ref_combo = pd.concat([ref_combo, ref_combo_cah], axis=0)
    pie_table = pd.merge(ref_combo, pred_combo, on='Ancestry Category')

    with pie1:
        st.markdown('### **Reference Panel Ancestry**')
        plot_pie(df_ref_ancestry_counts)

    with pie3:
        st.markdown(f'### {st.session_state["cohort_choice"]} Predicted Ancestry')
        plot_pie(df_pred_ancestry_counts)

    st.dataframe(
        pie_table[['Ancestry Category', 'Ref Panel Counts', 'Predicted Counts']],
        hide_index=True,
        use_container_width=True
    )


def render_tab_admix():
    """
    Render the Admixture Populations tab.

    Pulls admixture data from a known GCS location and displays
    the reference panel admixture table and plots.
    """
    frontend_bucket_name = 'gt_app_utils'
    frontend_bucket = get_gcloud_bucket(frontend_bucket_name)

    st.markdown('## **Reference Panel Admixture Populations**')
    with st.expander("Description"):
        st.write(config.DESCRIPTIONS['admixture'])

    ref_admix = blob_as_csv(frontend_bucket, 'ref_panel_admixture.txt')
    admix_plot_blob = frontend_bucket.get_blob('refpanel_admix.png')
    admix_plot = admix_plot_blob.download_as_bytes()
    st.image(admix_plot)

    admix_ancestry_select()
    admix_ancestry_choice = st.session_state['admix_ancestry_choice']

    if admix_ancestry_choice != 'All':
        ref_admix = ref_admix[ref_admix['ancestry'] == admix_ancestry_choice]

    st.dataframe(ref_admix, hide_index=True, use_container_width=True)
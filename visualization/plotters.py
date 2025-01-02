from typing import Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

class MetadataPlotter:
    @staticmethod
    def plot_age_distribution(data: pd.DataFrame, stratify: Optional[str] = None) -> go.Figure:
        """Create age distribution plot with optional stratification"""
        if stratify == 'Sex':
            fig = px.histogram(
                data, 
                x="Age", 
                color="Sex", 
                nbins=25, 
                color_discrete_map={'Male': "#332288", 'Female': "#CC6677"}
            )
            title = 'Age Distribution by Sex'
        elif stratify == 'Phenotype':
            fig = px.histogram(
                data, 
                x="Age", 
                color="Phenotype", 
                nbins=25,
                color_discrete_map={
                    'Control': "#332288",
                    'PD': "#CC6677",
                    'Other': "#117733",
                    'Not Reported': "#D55E00"
                }
            )
            title = 'Age Distribution by Phenotype'
        else:
            fig = px.histogram(
                data['Age'], 
                x='Age', 
                nbins=25, 
                color_discrete_sequence=["#332288"]
            )
            title = 'Age Distribution'
            
        fig.update_layout(title_text=f'<b>{title}<b>')
        return fig
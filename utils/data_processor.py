import pandas as pd
from typing import Optional

class DataProcessor:
    @staticmethod
    def process_master_key(master_key: pd.DataFrame, release_choice: int) -> pd.DataFrame:
        """Process master key data with consistent column names"""
        
        master_key = master_key[~master_key['nba_prune_reason'].isna()]
        # print(master_key)
        rename_map = {
                'age_at_sample_collection': 'Age',
                'biological_sex_for_qc': 'Sex',
                'baseline_GP2_phenotype_for_qc': 'Phenotype'
                
            }
        # if release_choice in [7, 8]:
        #     rename_map = {
        #         'age_at_sample_collection': 'Age',
        #         'biological_sex_for_qc': 'Sex',
        #         'baseline_GP2_phenotype_for_qc': 'Phenotype'
        #     }
        # elif release_choice == 6:
        #     rename_map = {
        #         'age': 'Age',
        #         'sex_for_qc': 'Sex',
        #         'gp2_phenotype': 'Phenotype'
        #     }
        # else:
        #     rename_map = {
        #         'age': 'Age',
        #         'sex_for_qc': 'Sex',
        #         'phenotype': 'Phenotype'
        #     }
        
        master_key = master_key.rename(columns=rename_map)
        
        sex_map = {1: 'Male', 2: 'Female', 0: 'Unknown'}
        master_key['Sex'] = master_key['Sex'].map(sex_map)
        
        return master_key

    @staticmethod
    def get_phenotype_counts(master_key: pd.DataFrame) -> pd.DataFrame:
        """Calculate phenotype counts split by sex"""
        male_pheno = master_key.loc[master_key['Sex'] == 'Male', 'Phenotype']
        female_pheno = master_key.loc[master_key['Sex'] == 'Female', 'Phenotype']
        
        combined_counts = pd.DataFrame({
            'Male': male_pheno.value_counts(),
            'Female': female_pheno.value_counts()
        })
        combined_counts['Total'] = combined_counts.sum(axis=1)
        return combined_counts.fillna(0).astype('int32')
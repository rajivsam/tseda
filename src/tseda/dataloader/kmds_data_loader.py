"""KMDS ontology read utilities for loading observations from a knowledge base."""

from owlready2 import *
from kmds.utils.load_utils import *
import pandas as pd

class KMDSDataLoader:
    """Read observation records from a KMDS OWL knowledge base into pandas DataFrames."""

    def __init__(self, file_path: str):
        """Load the KMDS ontology from *file_path*.

        Args:
            file_path: Absolute or relative path to an existing ``.xml`` / ``.rdf`` knowledge-base file.
        """
        self._file_path = file_path
        self._onto = self.load_kb()
        

        return
    
    def load_kb(self) -> Ontology:
        """Load the OWL knowledge base from the configured file path.

        Returns:
            Loaded ontology object.
        """
        onto2 :Ontology = load_kb(self._file_path)
        return onto2
    
    def load_exploratory_obs(self) -> pd.DataFrame:
        """Load exploratory observations from the workflow node.

        Returns:
            DataFrame with columns ``finding_seq`` and ``finding``.
        """
        

        the_workflow: Workflow = get_workflow(self._onto)
        exp_obs: List[ExploratoryObservation] = the_workflow.has_exploratory_observations
        records = []

        for o in exp_obs:
            a_row = {}
            a_row["finding_seq"] = o.finding_sequence
            #a_row["obs_type"] = o.exploratory_observation_type
            a_row["finding"] = o.finding
            records.append(a_row)
        df = pd.DataFrame(records)

        return df
    
    def load_data_rep_obs(self) -> pd.DataFrame:
        """Load data-representation observations from the workflow node.

        Returns:
            DataFrame containing sequence, observation type, and finding text.
        """
        the_workflow: Workflow = get_workflow(self._onto)
        dr_obs: List[DataRepresentationObservation] = the_workflow.has_data_representation_observations
        records = []
        for o in dr_obs:
            a_row = {}
            a_row["finding_seq"] = o.finding_sequence
            a_row["obs_type"] = o.data_representation_observation_type
            a_row["finding"] = o.finding
            records.append(a_row)
        df = pd.DataFrame(records)

        return df
    def load_modelling_choice_obs(self) -> pd.DataFrame:
        """Load modelling-choice observations from the workflow node.

        Returns:
            DataFrame containing sequence, observation type, and finding text.
        """
        the_workflow: Workflow = get_workflow(self._onto)
        mc_obs: List[ModellingChoiceObservation] = the_workflow.has_modelling_choice_observations
        records = []
        for o in mc_obs:
            a_row = {}
            a_row["finding_seq"] = o.finding_sequence
            a_row["obs_type"] = o.modelling_choice_observation_type
            a_row["finding"] = o.finding
            records.append(a_row)
        df = pd.DataFrame(records)

        return df   
    
    def load_modelling_selection_obs(self) -> pd.DataFrame:
        """Load modelling-selection observations from the workflow node.

        Returns:
            DataFrame containing sequence, observation type, and finding text.
        """
        the_workflow: Workflow = get_workflow(self._onto)
        ms_obs: List[ModellingSelectionObservation] = the_workflow.has_modelling_selection_observations
        records = []
        for o in ms_obs:
            a_row = {}
            a_row["finding_seq"] = o.finding_sequence
            a_row["obs_type"] = o.modelling_selection_observation_type
            a_row["finding"] = o.finding
            records.append(a_row)
        df = pd.DataFrame(records)

        return df
    
    def export_all_observations(self) -> pd.DataFrame:
        """Export all observation categories as a single table.

        Returns:
            Consolidated DataFrame containing exploratory, data representation,
            modelling choice, and modelling selection observations.
        """
        exp_df  = load_exp_observations(self._onto)
        dr_df = load_data_rep_observations(self._onto)
        mc_df = load_modelling_choice_observations(self._onto)
        ms_df = load_model_selection_observations(self._onto)
        df_consolidated = pd.concat([exp_df, dr_df, mc_df, ms_df], ignore_index=True)

        return df_consolidated
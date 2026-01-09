import kmds
from kmds.tagging.tag_types import DataRepresentationTags
from owlready2 import *
from kmds.utils.load_utils import *
from kmds.utils.path_utils import get_package_kb_path
import pandas as pd

class KMDSDataLoader:
    def __init__(self, file_path: str):
        self._file_path = file_path
        self._onto = self.load_kb()
        

        return
    
    def load_kb(self) -> Ontology:
        onto2 :Ontology = load_kb(self._file_path)
        return onto2
    
    def load_exploratory_obs(self) -> pd.DataFrame:
        

        the_workflow: Workflow = get_workflow(self._onto)
        exp_obs: List[ExploratoryObservation] = the_workflow.has_exploratory_observations
        records = []

        for o in exp_obs:
            a_row = {}
            a_row["finding_seq"] = o.finding_sequence
            #a_row["obs_type"] = o.exploratory_observation_type
            a_row["finding"] = o.finding
            records.append(a_row)
        df = DataFrame(records)

        return df
    


    
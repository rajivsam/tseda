from kmds.tagging.tag_types import ExploratoryTags
from kmds.ontology.intent_types import IntentType
from owlready2 import *
from kmds.utils.load_utils import *

class KMDSDataWriter:
    def __init__(self, file_path: str):
        self._file_path = file_path
        self._onto = self.load_kb()
        return
    
    def load_kb(self) -> Ontology:
        onto2 :Ontology = load_kb(self._file_path)
        return onto2
    
    def add_exploratory_obs(self, obs: str, file_path: str):
        the_workflow: Workflow = get_workflow(self._onto)


        
        with self._onto:
        # add the new observation
            observation_count :int = len(the_workflow.has_exploratory_observations)+ 1
            e1 = ExploratoryObservation(namespace=self._onto)

            e1.finding = obs
            e1.finding_sequence = observation_count
            e1.exploratory_observation_type = ExploratoryTags.DATA_QUALITY_OBSERVATION.value
            e1.intent = IntentType.DATA_UNDERSTANDING.value
            the_workflow.has_exploratory_observations.append(e1)

            self._onto.save(file=file_path, format="rdfxml")

        return

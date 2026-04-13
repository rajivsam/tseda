"""KMDS ontology write utilities for persisting exploratory observations."""

from kmds.tagging.tag_types import ExploratoryTags
from kmds.ontology.intent_types import IntentType
from owlready2 import *
from kmds.utils.load_utils import *

class KMDSDataWriter:
    """Write and mutate exploratory observations in a KMDS OWL knowledge base."""

    def __init__(self, file_path: str):
        """Load the KMDS ontology from *file_path*.

        Args:
            file_path: Absolute or relative path to an existing ``.xml`` / ``.rdf`` knowledge-base file.
        """
        self._file_path = file_path
        self._onto = self.load_kb()
        return
    
    def load_kb(self) -> Ontology:
        """Load and return the OWL knowledge base from the configured file path."""
        onto2 :Ontology = load_kb(self._file_path)
        return onto2
    
    def add_exploratory_obs(self, obs: str, file_path: str) -> None:
        """Append a new exploratory observation to the knowledge base and persist it.

        Args:
            obs: Text of the observation finding.
            file_path: Destination file path used when saving the updated ontology.
        """
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
    
    def delete_exploratory_obs(self, obs_seq: int) -> None:
        """Remove an exploratory observation by its 1-based sequence number.

        Args:
            obs_seq: 1-based index of the observation to delete.
        """
        the_workflow: Workflow = get_workflow(self._onto)
        with self._onto:
            del the_workflow.has_exploratory_observations[obs_seq - 1]

            obs_len = len(the_workflow.has_exploratory_observations)
            for idx in range(obs_len):
                the_workflow.has_exploratory_observations[idx].finding_sequence = idx + 1

            self._onto.save(file=self._file_path, format="rdfxml")

        return
    
    def update_exploratory_obs(self, obs: str, obs_seq: int) -> None:
        """Overwrite the finding text of an existing exploratory observation.

        Args:
            obs: Updated observation text.
            obs_seq: 1-based index of the observation to update.
        """
        the_workflow: Workflow = get_workflow(self._onto)
        with self._onto:
            the_workflow.has_exploratory_observations[obs_seq - 1].finding = obs

            self._onto.save(file=self._file_path, format="rdfxml")

        return



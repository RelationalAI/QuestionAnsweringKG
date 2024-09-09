import sys
import io
import ast
import json
from typing import Any, Dict, List, Tuple, Optional

def execute_query(pyrel_query: str, context: Dict[str, Any]) -> List: 
    """
    Executes the given PyRel query and returns the output.

    Args:
        pyrel_query (str): The PyRel query to be executed.
        context (dict): Additional context variables required for executing the query

    Returns:
        list: The output of the executed PyRel query.
    """

    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout

    try:
        # Execute the PyRel query within the provided context
        exec(pyrel_query, context)
    finally:
        # Restore the original stdout
        sys.stdout = old_stdout

    # Parse & return the output of the executed query
    output = ast.literal_eval(new_stdout.getvalue().strip())

    return output

#################################################################
    
class TripletClause:
    def __init__(self, triplet_object):
        """
        Initializes the TripletClause with a triplet object.

        Args:
            triplet_object: An instance of the Triplet class.
        """
        self.triplet_object = triplet_object

    def __call__(self, 
                 relation_candidate_ids: List[str], 
                 subject_candidate_ids: Optional[List[str]] = None, 
                 object_candidate_ids: Optional[List[str]] = None):
        """
        Creates a clause instance with specified candidate IDs.

        Args:
            relation_candidate_ids (list): List of relation candidate IDs.
            subject_candidate_ids (list, optional): List of subject candidate IDs. Defaults to None.
            object_candidate_ids (list, optional): List of object candidate IDs. Defaults to None.

        Returns:
            Triplet: An instance of the Triplet class with the specified candidate IDs.
        """

        # Create a Triplet instance
        triplet = self.triplet_object()

        # Assign relation IDs from the list of candidates
        triplet.rid.in_(relation_candidate_ids)

        # Assign subject IDs from the list of candidates, if provided
        if subject_candidate_ids:
            triplet.source_ent_id.in_(subject_candidate_ids)

        # Assign object IDs from the list of candidates, if provided
        if object_candidate_ids:
            triplet.target_ent_id.in_(object_candidate_ids)

        return triplet
    
    ###############################################################

def reformat_match_output(raw_output: Dict[str, List[List[Any]]]) -> Tuple[List[Dict], Dict[int, Dict]]:
    """    
    Reformats the output of the FAISS and prepare it for PyRel generation step
        
        Args:
            raw_output (Dict[str, List[List[Any]]]): The FAISS output as a dictionary where the value is a list of lists.
                Each inner list contains tuples, expected to contain at least three elements.
        
        Returns:
            Tuple[List[Dict], Dict[int, Dict]]: A tuple containing two elements:
                1. A list of dictionaries where each dictionary represents reformatted entries from the raw output.
                2. A dictionary of dictionaries, keyed by the original index of the entry, containing scores extracted from the similarity search step.
    """

    # Parse the JSON string into a dictionary 
    results = json.loads(raw_output)

    # Prepare containers for the reformatted output and scores
    reformatted_output = []
    scores = {}

    # Process each entry in the parsed results
    for idx, entry in enumerate(results):

        reformatted_output.append({j[0]:j[1] for j in entry})
        scores[idx] = {j[0]:j[2] for j in entry}

    return reformatted_output, scores
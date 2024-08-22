import sys
import io
import ast
from typing import Any, Dict, List, Optional

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
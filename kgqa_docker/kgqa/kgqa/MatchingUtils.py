from typing import List, Tuple
from kgqa.kgqa.Config import Config
import json
import requests

def compute_similar_entities(
    entity: str, num_qids=None, return_labels=False
) -> Tuple[List[str], List[float]]:
    """
    For a given entity specified in english, returns a list of lists of the follwing form,
    where each probability is the cosine similarity (inner product) with the given entity.

    Returns num_qids such entities.
    """
    config = Config()
    if num_qids is None:
        num_qids = config["NumTopQID"]
        
    url = "http://127.0.0.1:8000/compute_similar_entities"  
    
    payload = {
        "data": entity 
    }

    headers = {
        'Content-Type': 'application/json'
    }
    print(json.dumps(payload))
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    print(response.json())
    op = response.json()['data'][0][1]
    print("OP   ",op)
    if return_labels:
        return (
            op[0],
            op[2],
            op[1]
        )
    return op[0], op[2]


def compute_similar_properties(
    property: str, num_pids=None, return_labels=False
) -> Tuple[List[str], List[float]]:
    """
    For a given property specified in english, returns a list of properties,
    where each probability is the cosine similarity (inner product) with the given property.

    Returns num_pids such properties.
    """
    config = Config()
    if num_pids is None:
        num_pids = config["NumTopPID"]
    url = "http://127.0.0.1:8000/compute_similar_properties"  
    
    payload = {
        "data": property 
    }

    headers = {
        'Content-Type': 'application/json'
    }
    print(json.dumps(payload))
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    op = response.json()['data'][0][1]
    print("OP   ",op)
    if return_labels:
        return (
            op[0],
            op[2],
            op[1]
        )
    return op[0], op[2]

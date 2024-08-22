import requests
import numpy as np
from flask import make_response
import faiss
import json

# url = "http://127.0.0.1:8000/match"  
# url = "http://127.0.0.1:8000/getir"  
url = "http://127.0.0.1:8000/getquery"  
q = [0.1]*128
payload = {
    # "data":[[0,'X: actor(X, "The Silent One")']],
    # "data": [[0,'X, Y: director(X, "The 3 Stooges") ; main_subject(Y, "The 3 Stooges")' ]]
    "data":[[0,'Name a movie whose producer is the sibling of one of the cast members.','m: producer(m, x); cast_member(m, y); sibling(x, y)','[{"producer": ["P162", "P1431"]}, {"cast_member": ["P161", "P674"]}, {"sibling": ["P3373", "P8810"]}]']]
    # "data": [[0,'X: directed_by(X, "Srinu Vaitla"); cast_member(X, "Brahmanandam")']]
}

headers = {
    'Content-Type': 'application/json'
}
print(json.dumps(payload))
response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.json())

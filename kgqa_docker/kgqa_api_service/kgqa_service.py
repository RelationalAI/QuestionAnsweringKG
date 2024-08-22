from flask import Flask, request, make_response

from kgqa.kgqa.QueryParser import QueryParser
from kgqa.kgqa.QueryGraph import QueryGraphPropertyConstantNode, QueryGraphEntityConstantNode, QueryGraphPropertyNode
from kgqa.kgqa.QueryGraph import query2aqg, aqg2wqg
from kgqa.kgqa.QueryParser import QueryParser
from kgqa.kgqa.FaissIndex import FaissIndexDirectory
from QueryCortexAI.query_llm import query_llm
from QueryCortexAI.prompt_formatter import create_prompt_from_file
from kgqa.kgqa.Config import Config

import json, os
        
app = Flask(__name__)

@app.route('/getir', methods=['POST'])
def getir():
    message = request.json
        
    print(f'Received request: {message}')

    if message is None or not message['data']:
        print('Received empty message')
        return {}

    # input format:
    #   {"data": [
    #     [row_index, column_1_value, column_2_value, ...],
    #     ...
    #   ]}
    rows = message['data']
    head = "ir"

    # Read examples from JSON file
    prompt = create_prompt_from_file(prompt_file_path=os.path.join(os.getcwd(),'QueryCortexAI','heads',f"generate_{head}",'base_prompt.txt'),
                                     examples=json.load(open(os.path.join(os.getcwd(),'QueryCortexAI','heads',f"generate_{head}",'examples.json'))),
                                     question={'query':rows[0][1]})
    ir = query_llm(task=head, prompt=prompt, model=rows[0][2])
    print(ir)
    # ir = generate_ir(question=rows[0][1],base_prompt_path=os.path.join(os.getcwd(),'NLQtoIR','base_prompt.txt'),examples= json.load(open(os.path.join(os.getcwd(), 'NLQtoIR','ground_truth_data', 'examples.json'))))
    response = make_response({"data": [
            [0,ir]
            ]
        })
        
    response.headers['Content-type'] = 'application/json'
    return response

@app.route('/getquery', methods=['POST'])
def getpyrel():
    message = request.json
        
    print(f'Received request: {message}')

    if message is None or not message['data']:
        print('Received empty message')
        return {}

    # input format:
    #   {"data": [
    #     [row_index, column_1_value, column_2_value, ...],
    #     ...
    #   ]}
    rows = message['data']
    head = "pyrel"

    # Read examples from JSON file
    prompt = create_prompt_from_file(prompt_file_path=os.path.join(os.getcwd(),'QueryCortexAI','heads',f"generate_{head}",'base_prompt.txt'),
                                     examples=json.load(open(os.path.join(os.getcwd(),'QueryCortexAI','heads',f"generate_{head}",'examples.json'))),
                                     question={"query":rows[0][1],"IR":rows[0][2],"Similar_IDs":json.loads(rows[0][3])})
    pyrel = query_llm(task=head, prompt=prompt, model=rows[0][4])
    print(pyrel)
    # ir = generate_ir(question=rows[0][1],base_prompt_path=os.path.join(os.getcwd(),'NLQtoIR','base_prompt.txt'),examples= json.load(open(os.path.join(os.getcwd(), 'NLQtoIR','ground_truth_data', 'examples.json'))))
    response = make_response({"data": [
            [0,pyrel]
            ]
        })
        
    response.headers['Content-type'] = 'application/json'
    return response
    

@app.route('/match', methods=['POST'])
def match():
    message = request.json
        
    print(f'Received request: {message}')

    if message is None or not message['data']:
        print('Received empty message')
        return {}

    # input format:
    #   {"data": [
    #     [row_index, column_1_value, column_2_value, ...],
    #     ...
    #   ]}
    rows = message['data']
    print("INPUT DATA ",rows)
    # pq = QueryParser().parse(rows) # locally
    pq = QueryParser().parse(rows[0][1]) # Snowflake
    config = Config()["embeddings"]["transformer"]
    config["model"] = rows[0][2]
    aqg = query2aqg(pq)
    wqg = aqg2wqg(aqg)
    
    faiss = [[] for i in range(len(wqg.edges))]
    for edx, ed in enumerate(wqg.edges):
        src = ed.source
        tgt = ed.target
        prop = ed.property
        for node in [src, tgt, prop]:
            if isinstance(node, QueryGraphPropertyNode):
                faiss[edx].append([node.property, list(node.pids), list(node.scores)])
            if isinstance(node, QueryGraphPropertyConstantNode):
                faiss[edx].append([node.constant.value, list(node.pids), list(node.scores)])
            if isinstance(node, QueryGraphEntityConstantNode):
                faiss[edx].append([node.constant.value, list(node.qids), list(node.scores)])
    response = make_response({"data": [
            [0,faiss]
            ]
        })
        
    response.headers['Content-type'] = 'application/json'
    return response
    
    
@app.route('/compute_similar_properties', methods=['POST'])
def compute_similar_properties():
    message = request.json
        
    print(f'Received request: {message}')

    if message is None or not message['data']:
        print('Received empty message')
        return {}

    # input format:
    #   {"data": [
    #     [row_index, column_1_value, column_2_value, ...],
    #     ...
    #   ]}
    rows = message['data']
    print("INPUT DATA ",rows)
    # ids, labels, scores = FaissIndexDirectory().properties.search(
    #         rows[0][1], 5
    #     )
    ids, labels, scores = FaissIndexDirectory().properties.search(
            rows, 2
        )
    response = make_response({"data": [
            [0,[ids, labels, scores]]
            ]
        })
        
    response.headers['Content-type'] = 'application/json'
    return response
    
@app.route('/compute_similar_entities', methods=['POST'])
def compute_similar_entities():
    message = request.json
    print(f'Received request: {message}')

    if message is None or not message['data']:
        print('Received empty message')
        return {}

    # input format:
    #   {"data": [
    #     [row_index, column_1_value, column_2_value, ...],
    #     ...
    #   ]}
    rows = message['data']
    print("INPUT DATA ",rows)
    # ids, labels, scores = FaissIndexDirectory().labels.search(rows[0][1], 5)
    ids, labels, scores = FaissIndexDirectory().labels.search(rows, 2)
    response = make_response({"data": [
            [0,[ids, labels, scores]]
            ]
        })
        
    response.headers['Content-type'] = 'application/json'
    return response
    
    

# Health check endpoint
@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    return 'Service is up and running', 200

# Start the Flask application
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
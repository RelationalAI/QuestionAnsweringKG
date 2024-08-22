import subprocess, json
import getpass
import os
import subprocess

import time



def get_last_line(file_path):
    """Reads the last line of a file."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    return lines[-1].strip() if lines else ""

def load_config(config_path):
    """Load the configuration file.

    Args:
        config_path (str): The path to the JSON configuration file.

    Returns:
        dict: A dictionary containing configuration settings.
    """
    with open(config_path, 'r') as config_file:
        return json.load(config_file)


def main(options):
    config_path = options.get('config')
    config = load_config(config_path)
    config["account"] = config["account"].lower().replace("_","-")
    
     # Step 1: Authenticate Docker to interact with Snowflake
    password = getpass.getpass("Enter Snowflake password: ")
    file_name = "kgqa_similarity_search.tar"
    cont_name = "kgqa-cont"
    log_file = "./output.log"
    file_path = './sf_params.py'
    
    if not file_name.endswith(".gz"):
            file_name += ".gz"
    if not (os.path.isfile(file_name) or os.path.isfile(file_name+".gz")):
        print("Downloading Image from S3")
        s3_url = f"https://kgqa-wikidata.s3.us-east-2.amazonaws.com/{file_name}"
        print(f"{file_name} not found. Downloading...")
        curl_command = ['curl', '-o', file_name, s3_url]
        subprocess.run(curl_command, check=True)
        print("Download Completed\n")
        
    # Define your Snowflake parameters from config.json
    snowflake_params = {
        "user": config["sf_login_email"],
        "password": password,
        "account": config["account"],
        "warehouse": config["database"]["warehouse"]["name"],
        "database": config["database"]["name"],
        "schema": config["database"]["schema"],
        "role": config["roles"]["secondary"]
    }
    
    
    json_string = json.dumps(snowflake_params, indent=4)

    # Write the JSON string to the file
    with open(file_path, 'w') as file:
        # Write it as a valid Python dictionary
        file.write(f"connection_params = {json_string}\n")
    
    model = options.get('model',"e5-base-v2")
    
    subprocess.run(f"""docker run -d --name {cont_name} -v ./sf_params.py:/app/sf_params.py {file_name[:-7]} python3 setup.py ComputeEmbeddings --option model={model}""",shell=True, check=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    search_text = "✔  Computing Faiss Index..."
    check_interval = 2 * 60  # 2 minutes in seconds
    
    
    while(1):
        subprocess.run(f"""docker logs {cont_name} > {log_file} 2>&1""",shell=True, check=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        last_line = get_last_line(log_file)

        if search_text in last_line:
            print(f"Found the target text in the logs: {last_line}")
            break
        else:
            print(f"Target text not found. Sleeping for {check_interval / 60} minutes...")
            time.sleep(check_interval)
        
    
    subprocess.run(f"""docker cp {cont_name}:/app/data ./kgqa/""",shell=True, check=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    subprocess.run(f"""docker container rm {cont_name}""",shell=True, check=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    subprocess.run(f"""rm ./output.log""",shell=True, check=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(f"""rm ./sf_params.py""",shell=True, check=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
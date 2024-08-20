import subprocess, json
import getpass
import os


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
    output_dir = options.get('output_dir')
    config = load_config(config_path)
    config["account"] = config["account"].lower().replace("_","-")
    
     # Step 1: Authenticate Docker to interact with Snowflake
    password = getpass.getpass("Enter Snowflake password: ")
    login_command = f"""docker login {config["account"]}.registry.snowflakecomputing.com -u {config["sf_login_email"]} -p {password}"""
    subprocess.run(login_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Login Done\n")
    
    print("The below steps combined will take ~20 minutes, please wait.")
    if not options.get('push_only', False):
        
        # Step 2: Build the image
        print("Starting Build")
        build_command = f"""docker build --rm --platform linux/amd64 -t {config["account"]}.registry.snowflakecomputing.com/{config["database"]["name"]}/{config["database"]["schema"]}/{config["image_service"]["repo_name"]}/{config["image_service"]["image_name"]}:latest ."""
        subprocess.run(build_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Build Done\n")
        
        
    if options.get('push_only', False):
        file_name = "kgqa_image.tar"
        if not file_name.endswith(".gz"):
                file_name += ".gz"
        if not (os.path.isfile(file_name) or os.path.isfile(file_name+".gz")):
            print("Downloading Image from S3")
            s3_url = f"https://kgqa-wikidata.s3.us-east-2.amazonaws.com/{file_name}"
            print(f"{file_name} not found. Downloading...")
            curl_command = ['curl', '-o', file_name, s3_url]
            subprocess.run(curl_command, check=True)
            print("Download Completed\n")
        
        print("Loading the Image")
        load_from_zip_command = f"""docker load -i {file_name}"""
        subprocess.run(load_from_zip_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Loaded the image from Zip\n")
        
        
        tag_command = f"""docker tag kgqa_image {config["account"]}.registry.snowflakecomputing.com/{config["database"]["name"]}/{config["database"]["schema"]}/{config["image_service"]["repo_name"]}/{config["image_service"]["image_name"]}:latest"""
        subprocess.run(tag_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Retagged the image\n")
    


    # Step 3: Push the image
    print("Starting Push")
    push_command = f"""docker push {config["account"]}.registry.snowflakecomputing.com/{config["database"]["name"]}/{config["database"]["schema"]}/{config["image_service"]["repo_name"]}/{config["image_service"]["image_name"]}:latest"""
    subprocess.run(push_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Pushed the Image\n")

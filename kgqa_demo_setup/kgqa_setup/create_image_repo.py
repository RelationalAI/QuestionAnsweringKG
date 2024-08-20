import json
import argparse
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

def create_image_repo(config, output_dir):
    """Generates and saves SQL commands to create and manage an image repository based on the configuration.

    Args:
        config (dict): A dictionary containing configuration settings.
        output_dir (str): The directory where the SQL file will be saved.
    """
    use_commands = f"""
-- specify role + db + schema + warehouse to use for SQL commands execution
USE ROLE {config['roles']['secondary']};
USE DATABASE {config['database']['name']};
USE SCHEMA {config['database']['schema']};
USE WAREHOUSE {config['database']['warehouse']['name']};
    """

    create_repo = f"""
-- create image repository in SF which will host the docker image 
CREATE IMAGE REPOSITORY IF NOT EXISTS {config['image_service']['repo_name']};
GRANT READ, WRITE ON IMAGE REPOSITORY {config['image_service']['repo_name']} TO ROLE {config['roles']['secondary']};
    """
    
    list_all_repos = f"""
-- list all image repositories ( column repository_url will give the path where docker image will be pushed )
SHOW IMAGE REPOSITORIES;
"""
    
    list_images_in_repo = f"""
-- list all images in the repository
SHOW IMAGES in image repository {config['image_service']['repo_name']};
"""
    
    img_command = use_commands + create_repo + list_all_repos + list_images_in_repo

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Define the path for the SQL output file
    output_file_path = os.path.join(output_dir, 'image_repository_commands.sql')
    
    # Write img_command to an SQL file
    with open(output_file_path, 'w') as file:
        file.write(img_command)
    
    print("================================")
    print("\n ** COPY PASTE THE SQL COMMANDS IN ./image_repository_commands.sql TO SNOWFLAKE SQL WORKSHEET AND RUN THEM.\n**")
    print("================================")
   
def main(options):
    config_path = options.get('config')
    output_dir = options.get('output_dir')
    config = load_config(config_path)
    create_image_repo(config, output_dir)
    

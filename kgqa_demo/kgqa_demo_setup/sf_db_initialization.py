import os
import json
import argparse

def load_config(config_path):
    """Load the configuration file."""
    with open(config_path, 'r') as config_file:
        return json.load(config_file)

def create_populate_db(config, output_dir):
    """Generates and saves SQL commands to initialize and populate the database based on the configuration.

    Args:
        config (dict): A dictionary containing configuration settings.
        output_dir (str): The directory where the SQL file will be saved.

    """
    
    # SQL command to set the role, create the database, schema, and warehouse if they do not exist,
    # and set up a compute pool with specified configuration.
    create_command = f"""
-- initialize SF parameters
USE ROLE {config['roles']['primary']};
CREATE DATABASE IF NOT EXISTS {config['database']['name']};
CREATE SCHEMA IF NOT EXISTS {config['database']['schema']};
CREATE OR REPLACE WAREHOUSE {config['database']['warehouse']['name']} WITH WAREHOUSE_SIZE='{config['database']['warehouse']['size']}';
GRANT USAGE ON WAREHOUSE {config['database']['warehouse']['name']} TO ROLE {config['roles']['secondary']};
CREATE COMPUTE POOL IF NOT EXISTS {config['database']['compute_pool']['name']}
MIN_NODES = {config['database']['compute_pool']['min_nodes']}
MAX_NODES = {config['database']['compute_pool']['max_nodes']}
INSTANCE_FAMILY = {config['database']['compute_pool']['instance_family']};
GRANT USAGE, MONITOR ON COMPUTE POOL {config['database']['compute_pool']['name']} TO ROLE {config['roles']['secondary']};
    """

    # SQL command to specify the database, schema, and warehouse to be used.
    use_command = f"""
-- specify db + schema + warehouse to use for SQL commands execution
USE DATABASE {config['database']['name']};
USE SCHEMA {config['database']['schema']};
USE WAREHOUSE {config['database']['warehouse']['name']};
    """

    # SQL command to create a file format for CSV files and a stage for loading data.
    file_formatter = f"""
-- create file format and stage to load the CSV from S3 to SF
CREATE OR REPLACE FILE FORMAT {config['storage']['file_formatter_name']} TYPE = 'csv' FIELD_DELIMITER='\\t' SKIP_HEADER=1;
CREATE OR REPLACE STAGE {config['storage']['stage_name']} COMMENT = 'Loading data for QirK' URL = '{config['storage']['bucket_uri']}';
    """  

    # SQL command to create and populate tables.
    create_tables = f"""
-- create and populate tables
CREATE OR REPLACE TABLE id_labels(
    lid VARCHAR(30), 
    lname VARCHAR(200) 
);
COPY INTO id_labels FROM @{config['storage']['stage_name']}
    FILE_FORMAT = {config['storage']['file_formatter_name']}
    FILES = ('labels.csv');
    
CREATE OR REPLACE TABLE triplets(
    source_ent_id VARCHAR(30) NOT NULL,
    rid VARCHAR(30), 
    target_ent_id VARCHAR(30) NOT NULL
);
COPY INTO triplets (source_ent_id, rid, target_ent_id) FROM @{config['storage']['stage_name']}
    FILE_FORMAT = {config['storage']['file_formatter_name']}
    FILES = ('claims.csv');
    
CREATE OR REPLACE TABLE descriptions_en(
    did VARCHAR(30),
    descr VARCHAR(500) 
);
COPY INTO descriptions_en FROM @{config['storage']['stage_name']}
    FILE_FORMAT = {config['storage']['file_formatter_name']}
    FILES = ('descriptions.csv');
    
CREATE OR REPLACE TABLE triplets_inv AS
SELECT
    source_ent_id AS target_ent_id,
    rid,
    target_ent_id AS source_ent_id
FROM
    triplets
UNION ALL
SELECT
    target_ent_id,
    rid,
    source_ent_id
FROM
    triplets;

CREATE OR REPLACE TABLE entity_popularity AS (
SELECT source_ent_id AS id, COUNT(*) AS occur
FROM triplets_inv
GROUP BY source_ent_id
);

CREATE OR REPLACE TABLE property_popularity AS (
SELECT rid AS id, COUNT(*) AS occur
FROM triplets_inv
GROUP BY rid
);
    """

    # SQL commands to transfer ownership of the database, schemas, and tables to a secondary role.
    ownership = f"""
-- share ownership on SQL objects to secondary role
GRANT OWNERSHIP ON DATABASE {config['database']['name']} TO ROLE {config['roles']['secondary']} COPY CURRENT GRANTS;
GRANT OWNERSHIP ON ALL SCHEMAS IN DATABASE {config['database']['name']} TO ROLE {config['roles']['secondary']} COPY CURRENT GRANTS;
GRANT OWNERSHIP ON ALL TABLES IN DATABASE {config['database']['name']} TO ROLE {config['roles']['secondary']} COPY CURRENT GRANTS;
GRANT BIND SERVICE ENDPOINT ON ACCOUNT TO ROLE {config['roles']['secondary']};
    """

    # Combine all SQL commands
    init_command = create_command + use_command + file_formatter + create_tables + ownership

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Define the path for the SQL output file
    output_file_path = os.path.join(output_dir, 'db_initialization_commands.sql')

    with open(output_file_path, "w") as file:
        file.write(init_command)
    
    print("================================")
    print("\n ** COPY PASTE THE SQL COMMANDS IN ./db_initialization_commands.sql TO SNOWFLAKE SQL WORKSHEET AND RUN THEM.\n**")
    print("================================")
    
def main(options):
    config_path = options.get('config')
    output_dir = options.get('output_dir')
    config = load_config(config_path)
    create_populate_db(config, output_dir)
    

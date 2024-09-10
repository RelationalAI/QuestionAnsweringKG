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

def create_service(config, output_dir):
    """Generates and saves SQL commands to create and manage a service in Snowflake based on the configuration.

    Args:
        config (dict): A dictionary containing configuration settings.
        output_dir (str): The directory where the SQL file will be saved.
    """
    
    config["account"] = config["account"].lower().replace("_","-")
    use_commands = f"""
-- specify role + db + schema + warehouse to use for SQL commands execution
USE ROLE {config['roles']['secondary']};
USE DATABASE {config['database']['name']};
USE SCHEMA {config['database']['schema']};
USE WAREHOUSE {config['database']['warehouse']['name']};
    """

    drop_service = f"""
-- drop existing service
DROP SERVICE IF EXISTS {config['image_service']['service_name']};
    """

    image_path = (
        f"{config['account']}.registry.snowflakecomputing.com/" +
        f"{config['database']['name']}/{config['database']['schema']}/" +
        f"{config['image_service']['repo_name']}/{config['image_service']['image_name']}:latest"
    )

    create_service = f"""
-- create a new service which will provide endpoint to interact with the docker image
CREATE SERVICE {config['image_service']['service_name']}
IN COMPUTE POOL {config['database']['compute_pool']['name']}
FROM SPECIFICATION $$
spec:
    containers:
    - name: service-cont
      image: {image_path}
      env:
        SERVER_PORT: 8000
      readinessProbe:
        port: 8000
        path: /healthcheck
    endpoints:
    - name: service-endpoint
      port: 8000
      public: true
    $$
MIN_INSTANCES = 1
MAX_INSTANCES = 1
QUERY_WAREHOUSE = {config['database']['warehouse']['name']}
AUTO_RESUME = TRUE;
    """

    check_service_status = f"""
-- check status of the service
SELECT SYSTEM$GET_SERVICE_STATUS('{config['image_service']['service_name']}');
    """

    comment = """
-- WAIT FOR SERVICE STATUS TO BECOME READY (WAIT FOR AROUND 3-4 MINUTES)
"""

    check_container_logs = f"""
-- if run into some error while interacting with UDFs, user can check the container logs for error stack
SELECT SYSTEM$GET_SERVICE_LOGS('{config['image_service']['service_name']}', 0, 'service-cont', 1000);
    """

    create_udf = f"""
-- create UDFs to interact with the service
CREATE OR REPLACE FUNCTION generate_ir(nl varchar, model varchar)
RETURNS VARIANT
SERVICE = '{config['image_service']['service_name']}'
ENDPOINT='service-endpoint'
AS '/getir';


CREATE OR REPLACE FUNCTION make_ir_executable(nl varchar, model varchar)
RETURNS VARIANT
SERVICE = '{config['image_service']['service_name']}'
ENDPOINT='service-endpoint'
AS '/match';


CREATE OR REPLACE FUNCTION generate_query(nl varchar,ir varchar, faiss varchar, model varchar)
RETURNS VARIANT
SERVICE = '{config['image_service']['service_name']}'
ENDPOINT='service-endpoint'
AS '/getquery';
    """

    test_udf = """
-- test the UDFs with sample inputs
-- The second parameter is the model name. We have developed the pipeline using 'e5-base-v2' and 'llama3.1-70b.' Changing the model could affect the results. For more information, please refer to the [Snowflake documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions#availability).

SELECT generate_ir('Name a movie whose director is the sibling of one of the cast members.','llama3.1-70b') as result;
SELECT make_ir_executable('m: director(m, x); cast_member(m, y); sibling(x, y)','e5-base-v2') as result;
SELECT generate_query('Name a movie whose producer is the sibling of one of the cast members.','m: producer(m, x); cast member(m, y); sibling(x, y)','[{"producer": ["P162", "P1431"]}, {"cast member": ["P161", "P674"]}, {"sibling": ["P3373", "P8810"]}]','llama3.1-70b') as result;
    """

    service_command = use_commands + drop_service + create_service + check_service_status + comment + check_container_logs + create_udf + test_udf

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Define the path for the SQL output file
    output_file_path = os.path.join(output_dir, 'service_creation_commands.sql')
    
    # Write service_command to an SQL file
    with open(output_file_path, 'w') as file:
        file.write(service_command)
    
    print("================================")
    print("\n ** COPY PASTE THE SQL COMMANDS IN ./service_creation_commands.sql TO SNOWFLAKE SQL WORKSHEET AND RUN THEM.\n**")
    print("================================")

   
def main(options):
    config_path = options.get('config')
    output_dir = options.get('output_dir')
    config = load_config(config_path)
    create_service(config, output_dir)
    


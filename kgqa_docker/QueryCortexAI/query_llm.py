from snowflake import connector
import os
import sys

def get_login_token():
    with open('/snowflake/session/token', 'r') as f:
        return f.read()
    
def query_llm(task,
              prompt,
              model="llama3.1-70b",
              service_run=True):
    """
    Generates a PyRel query using the provided base prompt, examples, and question.

    Args:
        task (str): "ir" or "pyrel"
        prompt (str): prompt for the LLM
        model (str): Name of the LLM to use for the query.
        service_run (bool): Set as False, if you want to run locally for experimentation 

    Returns:
        str: The generated PyRel query.
    """ 
    if task in ["ir", "pyrel"]:

        if service_run:
        
            connection = connector.connect(
            host = os.getenv('SNOWFLAKE_HOST'),
                account = os.getenv('SNOWFLAKE_ACCOUNT'),
                token = get_login_token(),
                authenticator = 'oauth',
                database = os.getenv('SNOWFLAKE_DATABASE'),
                schema = os.getenv('SNOWFLAKE_SCHEMA')
                )
        else:
            sys.path.insert(0, os.path.dirname(os.getcwd()))
            from docker_utility.sf_params import connection_params
            connection = connector.connect(**connection_params)

        cursor = connection.cursor()

        # Query the Cortex AI model with the generated promp
        escaped_prompt = prompt.replace("'", "''")
        sql_query = f""" 
        SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', '{escaped_prompt}') AS RESULT;
        """

        cursor.execute(sql_query)
        output = cursor.fetchone()[0]
    else:
        raise ValueError("Invalid task. It must be either ir or pyrel.")

    if task == "pyrel":
        output += "\nprint(results)"

    return output


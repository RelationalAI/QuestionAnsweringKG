import json
import getpass

config = json.load(open("../kgqa_setup/config.json"))

connection_params = {
    'user': config["sf_login_email"],
    'password': getpass.getpass("Enter Snowflake password: "),
    "account": config["account"],
    "warehouse": config["database"]["warehouse"]["name"],
    "database": config["database"]["name"],
    "schema": config["database"]["schema"],
    "role":config["roles"]["secondary"]
}
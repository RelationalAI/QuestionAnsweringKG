## Launch a SF Service on a Custom Database

Follow the below steps to launch End-to-End pipeline as a Service on Snowflake and interact with it.


 
### SETTING THE ENVIRONMENT VARIABLES

**<your_project_repository> is the path to the local directory where <git_repo> has been cloned.**


```sh
export SETUP_PATH="<your_project_directory>/kgqa_demo_setup/kgqa_setup"
```


### STEP 1 : Navigate to the KGQA_DOCKER FOLDER
```sh
cd <your_project_directory>/kgqa_docker/
```

### STEP 2 : Populate all SF config parameters

- Update the config parameters in the config file ['config.json'](./kgqa_demo_setup/kgqa_setup/config.json)

> **_NOTE:_** Anything prefixed with **temp_** can be customized by the user, along with **account and sf_login_email**. *Everything else should remain unchanged*.

### STEP 3 : Initializing database in Snowflake - *Copy Paste Output to SF Worksheet and Run*

*Execute the below **sf_db_initialization** script to produce SQL File to load and populate the Database and Tables in Snowflake ( copy-paste on Snowflake SQL Worksheet and Run)*

> **_NOTE:_** To execute SQL commands in Snowflake Worksheet, you first need to select a database. Initially, this could be any database. Later in the script, you will create a custom database and switch to it for subsequent commands.

```sh
python3 $SETUP_PATH/setup.py --config $SETUP_PATH/config.json --output_dir $SETUP_PATH/ sf_db_initialization
```

### STEP 4 : Image Repository Creation - *Copy Paste Output to SF Worksheet and Run*

An Image Repository in Snowflake is a storage location where you can store and manage container images. These images are like snapshots of applications and their environments, which can be run on Snowflake's platform.

*Execute the below **create_image_repo** script to produce SQL File to create Image Repository on Snowflake ( copy-paste on Snowflake SQL Worksheet and Run)*

```sh
python3 $SETUP_PATH/setup.py --config $SETUP_PATH/config.json --output_dir $SETUP_PATH/ create_image_repo
```


### STEP 5 : Generate FAISS Index Files

The Similarity Search using FAISS relies on index files to find the best matching results. These index files must be included in the container image for the search to function properly.

*Execute the below **generate_embeddings** script to create the index files*

```sh
python3 $SETUP_PATH/setup.py --config $SETUP_PATH/config.json --output_dir $SETUP_PATH/ generate_embeddings --option model="e5-base-v2"
```

### STEP 6 : Push Image to Snowflake Image Repository

*Execute the below **build_push_docker_image** script to push docker image to Snowflake's Image Repository.*

```sh
python3 $SETUP_PATH/setup.py --config $SETUP_PATH/config.json --output_dir $SETUP_PATH/ build_push_docker_image
```


### STEP 7 : Launch a Snowflake service - *Copy Paste Output to SF Worksheet and Run*

*Execute the below **create_service** script to produce SQL File to create Snowflake Service ( copy-paste on Snowflake SQL Worksheet and RUN)*

```sh
python3 $SETUP_PATH/setup.py --config $SETUP_PATH/config.json --output_dir $SETUP_PATH/ create_service
```

> **_NOTE:_** After running the "*CREATE SERVICE ..*" command in SF Worksheet, wait for the service to get **Status="READY"** ( takes around 3-4 minutes ) before creating the UDFs and testing them in the below Worksheet.


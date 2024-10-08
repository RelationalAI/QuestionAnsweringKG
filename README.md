# KGQA: Question Answering on Knowledge Graphs Using RelationalAI and Snowflake Cortex AI

Knowledge graphs are a useful structure to use to encode information about a particular domain. They allow for explicit inspection of the data encoded and the ability to reason over the relations. However, writing a query against a knowledge graph can be more challenging than other systems given that they generally lack a natural language interface. In order to query over a knowledge graph such as the one created by Wikidata, the user must know the specialized syntax of SPARQL as well as the knowledge graph representation of the entities and relations. For example, the concept of a hospital in wikidata is represented internally as Q16917.

**KGQA allows users to query a knowledge graph (KG) using natural language.** This enables a user to run a query over a knowledge graph by simply stating the question.

This demo will create a Snowflake service using Snowpark Container Services ( SPCS ), Snowflake's LLM service provided by their Cortex product and RelationalAI, a Knowledge Graph Coprocessor embedded inside of Snowflake, to allow a user to ask the following questions on a subset of Wikidata:

- List movies directed by John Krasinski?
- Name a movie directed by Quentin Tarantino or Martin Scorsese that has De Niro as a cast member
- Which movie's director was born in the same city as one of the cast members?
....

Additional examples in the demo notebook.

*This work is a partial reimplementation of the [QirK: Question Answering via Intermediate Representation on Knowledge Graphs paper](https://arxiv.org/abs/2408.07494). The implementation of the paper can be found [here](https://github.com/jlscheerer/kgqa/tree/main).*

----------

## Demo Setup

Follow the below steps to launch End-to-End Demo Setup.


> **_NOTE:_** User's Role permissions <br>
> Users should have access to role "kgqa_public" in their snowflake account, which has ownership and usage access similar to "accountadmin". Follows ths steps mentioned [here](https://docs.snowflake.com/en/user-guide/security-access-control-configure#create-a-role) to create a new role. 
 
### SETTING THE ENVIRONMENT VARIABLES

**<your_project_repository> is the path to the local directory where <git_repo> has been cloned.**


```sh
export SETUP_PATH="<your_project_directory>/kgqa_demo/kgqa_demo_setup"
```


#### STEP 1 : Navigate to the KGQA_SETUP FOLDER
```sh
cd $SETUP_PATH
```

#### STEP 2 : Populate all Snowflake config parameters 

- Update the config parameters in the config file ['config.json'](./kgqa_demo/kgqa_demo_setup/config.json)
> **_NOTE:_** Anything prefixed with **temp_** can be customized by the user, along with **account and sf_login_email**. *Everything else should remain unchanged*.

#### STEP 3 : Initializing database in Snowflake - *Copy Paste Output to SF Worksheet and Run*

*Execute the below **sf_db_initialization** script to produce SQL File to load and populate the Database and Tables in Snowflake ( copy-paste on Snowflake SQL Worksheet and Run).*

```sh
python3 $SETUP_PATH/setup.py --config $SETUP_PATH/config.json --output_dir $SETUP_PATH/ sf_db_initialization
```

This step will automatically download [triplets](https://kgqa-wikidata.s3.us-east-2.amazonaws.com/wiki_sample_snapshot/claims.csv) and [labels](https://kgqa-wikidata.s3.us-east-2.amazonaws.com/wiki_sample_snapshot/labels.csv) files from AWS S3 Bucket and load the data in Snowflake.

> **_NOTE:_** To execute SQL commands in Snowflake Worksheet, you first need to select a database. Initially, this could be any database. Later in the script, you will create a custom database and switch to it for subsequent commands.

#### STEP 4 : Image Repository Creation - *Copy Paste Output to SF Worksheet and Run*

An Image Repository in Snowflake is a storage location where you can store and manage container images. These images are like snapshots of applications and their environments, which can be run on Snowflake's platform.

*Execute the below **create_image_repo** script to produce SQL File to create Image Repository on Snowflake ( copy-paste on Snowflake SQL Worksheet and Run)*

```sh
python3 $SETUP_PATH/setup.py --config $SETUP_PATH/config.json --output_dir $SETUP_PATH/ create_image_repo
```

#### STEP 5 : Push Image to Snowflake Image Repository

*Execute the below **build_push_docker_image** script to push docker image to Snowflake's Image Repository.*

```sh
python3 $SETUP_PATH/setup.py --config $SETUP_PATH/config.json --output_dir $SETUP_PATH/ build_push_docker_image --option push_only=True
```

- push_only parameter ensures that we don't re-execute the docker commands to build a new image. We download the existing pre-built image, and push it to our Snowflake Image Repository defined in the previous step. 


#### STEP 6 : Launch a Snowflake service - *Copy Paste Output to SF Worksheet and Run*

*Execute the below **create_service** script to produce SQL File to create Snowflake Service ( copy-paste on Snowflake SQL Worksheet and RUN)*

```sh
python3 $SETUP_PATH/setup.py --config $SETUP_PATH/config.json --output_dir $SETUP_PATH/ create_service
```
> **_NOTE:_** After running the "*CREATE SERVICE ..*" command in SF Worksheet, wait for the service to get **Status="READY"** ( takes around 3-4 minutes ) before creating the UDFs and testing them in the below Worksheet. 


Now, we are all set to run the Demo notebook!

------------------------------------------------------------------


## Demo Notebook 

### STEP 1 : Create API Integration
- Open a SQL Worksheet on Snowflake and execute the following command on your database and schema as defined in the [config.json](https://github.com/RelationalAI/QuestionAnsweringKG/blob/main/kgqa_demo/kgqa_demo_setup/config.json). 

```sql
USE ROLE ACCOUNTADMIN; 

CREATE OR REPLACE API INTEGRATION git_api_integration
  API_PROVIDER = git_https_api
  API_ALLOWED_PREFIXES = ('https://github.com/RelationalAI')
  ENABLED = TRUE;
```
### STEP 2 : Create a Git Repository Stage on Snowflake
- Then, follow the instructions [here](https://docs.snowflake.com/en/developer-guide/git/git-setting-up#label-integrating-git-repository-api-integration) to create a git repository stage in Snowflake. *NOTE - No secret is needed, since it is a public repository.*
    - Remote Repository URL - https://github.com/RelationalAI/QuestionAnsweringKG.git

### STEP 3 : Load the Demo Notebook as Snowflake Notebook
- Go to [https://app.snowflake.com](https://app.snowflake.com) and under Projects->Notebooks, on the top right corner in Notebook Dropdown, select *Create from Repository*. 
    - For *File Location in Repository* , navigate to the Git repository stage created in previous step, and select *`kgqa_demo->kgqa_demo.ipynb`*.
    - Fill the rest of the details as defined in the [config.json](https://github.com/RelationalAI/QuestionAnsweringKG/blob/main/kgqa_demo/kgqa_demo_setup/config.json). 

### STEP 4 : Load RelationalAI in Snowflake Notebook
- Load RelationalAI in Snowflake Notebook using [Installation Guide](https://relational.ai/docs/native_app/installation#ii-set-up-the-rai-native-app). 
    - *Place the `relationalai.zip` file, as specified in the instructions, in the same directory as `kgqa_demo.ipynb` within Snowflake.*
    
Run the [KGQA Demo Notebook](https://github.com/RelationalAI/QuestionAnsweringKG/blob/main/kgqa_demo/kgqa_demo.ipynb) in Snowflake to play with our pipeline!


------------------------------------------------------------------

### Troubleshooting

In case you encounter any of the following issues, please follow the recommended steps:

1. **Server Overload Error**
   If the Snowflake server becomes unresponsive and shows a 'Server overloaded' error:
   - To resolve the issue, run the script generated from **[Demo Setup -> Step 6]** from Line that says *"DROP SERVICE IF EXISTS..."*


2. **Model Unavailable Error**
    The default models during development are lama3.1-70b for Snowflake Complete Task and e5-base-v2 for Snowflake Text Embedding Task. In case these models are not ['available in the region'](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions#availability), run the script generated **[Demo Setup -> Step 6]**  from Line that says   *"-- test the UDFs with sample inputs"*  with chosen model name, available in your region.<br><br>

    **2.1** IF the text embedding model is changed from e5-base-v2 to something else, follow the **[Launch a SF Service on Custom Database -> Steps 5 through 7]**. <br>
        - *Since the Dockerfile is present inside **kgqa_docker** folder, remember to  Switch to **kgqa_docker** folder to follow them.*

------------------------------------------------------------------


### Launch a SF Service on a Custom Database

If you would like to build and launch the service with a custom database, follow our instructions in our [CustomDatabase](CustomDatabase.md) section

------------------------------------------------------------------

### APPENDIX

If you would like help with Docker or Snowflake commands, see our [Appendix](Appendix.md)

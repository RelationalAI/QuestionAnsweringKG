from sentence_transformers import SentenceTransformer

from kgqa.kgqa.Singleton import Singleton
from kgqa.kgqa.Config import Config
import snowflake.connector
import os
import numpy as np

def get_login_token():
    with open('/snowflake/session/token', 'r') as f:
        return f.read()
            
class Transformer(metaclass=Singleton):
    def __init__(self):
        # self._model = SentenceTransformer("./sent_trans_model/")
        self.config = Config()["embeddings"]["transformer"]
        self.conn = snowflake.connector.connect(
            host = os.getenv('SNOWFLAKE_HOST'),
            account = os.getenv('SNOWFLAKE_ACCOUNT'),
            token = get_login_token(),
            authenticator = 'oauth',
            database = os.getenv('SNOWFLAKE_DATABASE'),
            schema = os.getenv('SNOWFLAKE_SCHEMA')
        )
        # from docker_utility.sf_params import connection_params
        # self.conn = snowflake.connector.connect(**connection_params)

    def encode(self, words):
        if isinstance(words, list):
            words = [w.replace("'", "''") for w in words]
            values_clause = ", ".join([f"('{w}')" for w in words])
            query = f"""SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('{self.config["model"]}', t.VALUE) AS embedding FROM (VALUES {values_clause}) AS t(VALUE)"""
            result = self.conn.cursor().execute(query).fetch_pandas_all()
            embeddings_array = [row for row in result.EMBEDDING]
            embeddings_array = np.array(embeddings_array)
        else:
            query = f"""SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('{self.config["model"]}', %s) AS embedding"""
            result = self.conn.cursor().execute(query, (words,)).fetch_pandas_all()
            embeddings_array = result.EMBEDDING[0]
        return embeddings_array

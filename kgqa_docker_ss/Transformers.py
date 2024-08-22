from Singleton import Singleton
import snowflake.connector
import os
import numpy as np

class Transformer(metaclass=Singleton):
    def __init__(self):
        
        from sf_params import connection_params
        self.conn = snowflake.connector.connect(**connection_params)

    def encode(self, words, model="e5-base-v2"):
        if isinstance(words, list):
            words = [w.replace("'", "''") for w in words]
            values_clause = ", ".join([f"('{w}')" for w in words])
            query = f"""SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('{model}', t.VALUE) AS embedding FROM (VALUES {values_clause}) AS t(VALUE)"""
            result = self.conn.cursor().execute(query).fetch_pandas_all()
            embeddings_array = [row for row in result.EMBEDDING]
            embeddings_array = np.array(embeddings_array)
        else:
            query = f"""SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('{model}', %s) AS embedding"""
            result = self.conn.cursor().execute(query, (words,)).fetch_pandas_all()
            embeddings_array = result.EMBEDDING[0]
        return embeddings_array

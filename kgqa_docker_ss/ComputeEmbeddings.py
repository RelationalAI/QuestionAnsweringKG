import os
import re

import numpy as np
from yaspin import yaspin
from tqdm import tqdm


from Config import Config
from Database import Database
from FileUtils import partioned_files_in_directory, read_strs_from_file
from Transformers import Transformer
from Constants import *
import faiss
from FaissIndex import faiss_id_to_int, faiss_int_to_id



def _dump_strs_to_file(filename, data):
    with open(filename, "w") as file:
        file.writelines([f"{x}\n" for x in data])


def _read_strs_from_file(filename):
    with open(filename, "r") as file:
        return [x.strip() for x in file.readlines()]


def extract_db_labels():
    config = Config()
    db = Database()

    sql = f"""SELECT * 
    FROM id_labels 
    WHERE lid LIKE 'Q%' 
    ORDER BY TO_NUMBER(REGEXP_SUBSTR(lid, '[0-9]+$'))::INT;"""

    BATCH_SIZE = config["embeddings"]["batch_size"]
    with yaspin(text="Extracting Labels...") as sp:
        for index, rows in enumerate(db.fetchmany(sql, BATCH_SIZE)):
            low, high = index * BATCH_SIZE, index * BATCH_SIZE + len(rows) - 1
            ids, labels = zip(*rows)

            ids_file = config.file_in_directory("embeddings", f"qids_{low}_{high}.txt")
            _dump_strs_to_file(ids_file, ids)

            labels_file = config.file_in_directory(
                "embeddings", f"labels_{low}_{high}.txt"
            )
            _dump_strs_to_file(labels_file, labels)

        sp.green.ok("✔ ")


def compute_label_embeddings(model="e5-base-v2"):
    config = Config()

    for file in tqdm(os.listdir(config.directory("embeddings"))):
        if not re.match("^labels_[0-9]+_[0-9]+\\.txt$", file):
            continue
        labels = _read_strs_from_file(
            os.path.join(config.directory("embeddings"), file)
        )
        low, high = [*map(int, file[len("labels_") : -len(".txt")].split("_"))]

        embeddings_file = config.file_in_directory(
            "embeddings", f"emb_{low}_{high}.npy"
        )
        embeddings = Transformer().encode(labels, model=model)
        np.save(embeddings_file, embeddings)


def _preprocess_ids_to_np(filename):
    ids_txt = read_strs_from_file(filename)
    return np.array([faiss_id_to_int(id) for id in ids_txt], dtype=np.int64)


def _emb_file_to_qids_file(filename):
    assert filename.startswith("emb_")
    assert filename.endswith(".npy")
    return f'qids_{filename[len("emb_"):-len(".npy")]}.txt'


def _get_label_embeddings_files():
    return partioned_files_in_directory("embeddings", "emb", "npy")


def _get_label_id_files():
    return partioned_files_in_directory("embeddings", "qids", "txt")


def _get_label_ids():
    config = Config()
    return np.concatenate(
        [
            _preprocess_ids_to_np(config.file_in_directory("embeddings", file))
            for file in _get_label_id_files()
        ]
    )


def _load_label_embeddings():
    config = Config()
    return np.concatenate(
        [
            np.load(config.file_in_directory("embeddings", label_embeddings_file))
            for label_embeddings_file in _get_label_embeddings_files()
        ]
    )


def compute_faiss_index():
    config = Config()

    EMBEDDINGS_SIZE = 768  # embeddings.shape[1]
    factory_settings = "Flat"

    num_files_per_shard = config["embeddings"]["count"] // config["embeddings"]["batch_size"]
    embeddings_files = _get_label_embeddings_files()

    for shard_start_index in range(0, len(embeddings_files), num_files_per_shard):
        print(f"Constructing Index for shard-{shard_start_index // num_files_per_shard}")
        embeddings_idx = faiss.index_factory(
            EMBEDDINGS_SIZE, factory_settings, faiss.METRIC_INNER_PRODUCT
        )
        idx = faiss.IndexIDMap(embeddings_idx)
        for label_embeddings_file in tqdm(embeddings_files[shard_start_index : shard_start_index + num_files_per_shard]):
            file = config.file_in_directory("embeddings", label_embeddings_file)
            ids = _preprocess_ids_to_np(
                config.file_in_directory(
                    "embeddings", _emb_file_to_qids_file(label_embeddings_file)
                )
            )
            embeddings = np.load(file)
            idx.add_with_ids(embeddings, ids)

        faiss.write_index(idx, config.file_in_directory("embeddings", f"shard{shard_start_index // num_files_per_shard}_{FILENAME_FAISS_INDEX}"))


def extract_db_properties_en():
    config = Config()
    db = Database()

    sql = """
    SELECT * 
    FROM id_labels 
    WHERE lid LIKE 'P%' 
    ORDER BY TO_NUMBER(REGEXP_SUBSTR(lid, '[0-9]+$'))::INT;
    """

    with yaspin(text="Extracting Properties...") as sp:
        property_ids, property_values = [], []
        for id, value in db.fetchall(sql):
            property_ids.append(id)
            property_values.append(value)

        ids_file = config.file_in_directory("embeddings", FILENAME_PROPERTY_IDS)
        _dump_strs_to_file(ids_file, property_ids)

        values_file = config.file_in_directory("embeddings", FILENAME_PROPERTY_LABELS)
        _dump_strs_to_file(values_file, property_values)

        sp.green.ok("✔ ")


def compute_property_embeddings(model="e5-base-v2"):
    config = Config()

    with yaspin(text="Computing Property Embeddings...") as sp:
        values_file = config.file_in_directory("embeddings", FILENAME_PROPERTY_LABELS)
        values = _read_strs_from_file(values_file)

        embeddings = Transformer().encode(values, model=model)
        embeddings_file = config.file_in_directory(
            "embeddings", FILENAME_PROPERTY_EMBEDDINGS
        )
        np.save(embeddings_file, embeddings)

        sp.green.ok("✔ ")


def compute_property_faiss_index():
    config = Config()

    with yaspin(text="Computing Faiss Index...") as sp:
        embeddings = np.load(
            config.file_in_directory("embeddings", FILENAME_PROPERTY_EMBEDDINGS)
        )
        ids = _preprocess_ids_to_np(
            config.file_in_directory("embeddings", FILENAME_PROPERTY_IDS)
        )
        factory_settings = "Flat"
        embeddings_idx = faiss.index_factory(
            embeddings.shape[1], factory_settings, faiss.METRIC_INNER_PRODUCT
        )
        idx = faiss.IndexIDMap(embeddings_idx)
        idx.add_with_ids(embeddings, ids)

        faiss.write_index(
            idx, config.file_in_directory("embeddings", FILENAME_PROPERTY_FAISS)
        )

        sp.green.ok("✔ ")



def accept(options):
    # Label Embeddings
    if not options.get("skip_extract_labels", False):
        extract_db_labels()
    if not options.get("skip_label_embeddings", False):
        compute_label_embeddings(model=options.get('model', 'e5-base-v2'))

    # Faiss Index for Labels + Aliases
    if not options.get("skip_faiss", False):
        compute_faiss_index()

    # Property Embeddings
    if not options.get("skip_extract_properties", False):
        extract_db_properties_en()
    if not options.get("skip_property_embeddings", False):
        compute_property_embeddings(options.get('model', 'e5-base-v2'))

    if not options.get("skip_property_faiss", False):
        compute_property_faiss_index()
        

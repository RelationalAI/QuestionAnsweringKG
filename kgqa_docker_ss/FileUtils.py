import os
import re
import pickle

from Config import Config


def read_strs_from_file(filename):
    with open(filename, "r") as file:
        return [x.strip() for x in file.readlines()]


def load_pickle_from_file(filename):
    with open(filename, "rb") as file:
        return pickle.load(file)


def partioned_files_in_directory(directory, prefix, extension="txt"):
    config = Config()
    files = []
    for file in os.listdir(config.directory(directory)):
        if not re.match(f"^{prefix}_[0-9]+_[0-9]+\\.{extension}$", file):
            continue
        low, high = [
            *map(int, file[(len(prefix) + 1) : -(len(extension) + 1)].split("_"))
        ]
        files.append((file, low, high))
    files.sort(key=lambda x: x[1])
    return [x[0] for x in files]


def read_partioned_strs(directory, prefix, extension="txt"):
    config = Config()
    return sum(
        [
            read_strs_from_file(config.file_in_directory(directory, filename))
            for filename in partioned_files_in_directory(directory, prefix, extension)
        ],
        [],
    )

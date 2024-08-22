import yaml
import os

from Singleton import Singleton

DEFAULT_CONFIG_PATH = "./config.yaml"


class Config(metaclass=Singleton):
    def __init__(self):
        if not os.path.exists(DEFAULT_CONFIG_PATH):
            raise AssertionError(f"Failed to load config: '{DEFAULT_CONFIG_PATH}'")
        with open(DEFAULT_CONFIG_PATH, "r") as file:
            config = yaml.safe_load(file)
        self._config = config

    def __getitem__(self, item):
        try:
            return self._config[item]
        except Exception:
            raise AssertionError(f"config is missing required parameter: {item}")

    def get_or_default(self, item, default):
        if item in self._config:
            return self._config[item]
        return default

    def directory(self, directory):
        path = self[directory]["directory"]
        return os.path.abspath(path)

    def file_in_directory(self, directory, filename):
        path = self.directory(directory)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return os.path.join(path, filename)

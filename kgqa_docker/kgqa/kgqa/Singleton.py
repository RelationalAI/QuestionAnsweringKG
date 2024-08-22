from typing import Dict


class Singleton(type):
    """
    A metaclass that creates a Singleton base when called.
    Example usage: Database(metaclass=Singleton)
    """

    # Maps a class to the correspoding singleton.
    _instance: Dict[type, type] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance[cls]

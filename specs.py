from pathlib import Path
from typing import Mapping, Sequence, TextIO, Union
import yaml
from jar_providers import BaseJar


class Specification:
    _data: dict

    server: BaseJar
    plugins: Sequence[BaseJar]

    def __init__(self, data: Mapping):
        self._data = data

        self.server = BaseJar(data["server"])
        self.plugins = [BaseJar(p) for p in data["plugins"]]

    @classmethod
    def from_yaml(cls, data: Union[str, TextIO]):
        return cls(yaml.safe_load(data))

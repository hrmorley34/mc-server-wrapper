from abc import ABC, abstractmethod
import collections.abc
from pathlib import Path
import shutil
from typing import Mapping, MutableMapping, Optional, Type, Union


def convert_data(data: Union[Mapping, str]) -> dict:
    if isinstance(data, collections.abc.Mapping):
        return dict(data)
    return {"type": data}


def err_if_data(data: Mapping, name: Optional[str] = None):
    "Error if there are keys left in `data`"
    if "type" in data:  # ignore existance of "type"
        data = dict(data)
        data.pop("type")
    if data:
        keysstr = ", ".join(map(str, data.keys()))
        tostr = "" if name is None else f" to {name}"
        raise ValueError(f"Unexpected arguments{tostr}: {keysstr}")


class BaseJar(ABC):
    "Represents an accessor for a Jar file"

    handlers: MutableMapping[Optional[str], Type["BaseJar"]] = {}

    def __new__(cls, data: Union[Mapping, str]) -> "BaseJar":
        "If a BaseJar is called, create a jar of the appropriate `data[\"type\"]`"
        if cls is BaseJar:  # not on subtype
            if isinstance(data, collections.abc.Mapping):
                t: Optional[str] = data.get("type")
            else:
                t = data  # a lone name is used as a type without arguments

            if t in cls.handlers:
                return object.__new__(cls.handlers[t])
            else:
                raise ValueError(f"Unknown jar type: {t}")
        return object.__new__(cls)

    def __init__(self, data: Union[Mapping, str]):
        pass

    @abstractmethod
    def fetch(self, dest: Path) -> Path:
        pass


class FileJar(BaseJar):
    "Jar located on the local filesystem"

    path: Path

    def __init__(self, data: Union[dict, str]):
        data = convert_data(data)

        data.pop("type", None)
        self.path = Path(data.pop("path"))

        err_if_data(data, "FileJar")

    def fetch(self, dest: Path) -> Path:
        return shutil.copy2(self.path, dest)


BaseJar.handlers["file"] = BaseJar.handlers[None] = FileJar

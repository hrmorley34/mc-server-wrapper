from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256
from pathlib import Path
import pickle
from typing import Any
from .base import YamlObject


class BaseStore(ABC, YamlObject):
    @abstractmethod
    def fetch(self, key: Any) -> Path | None:
        pass

    @abstractmethod
    def get_name(self, key: Any) -> Path:
        pass


class Store(BaseStore, yamltag="!store.default"):
    directory: Path

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def get_key(self, obj: Any) -> Path:
        p = pickle.dumps(obj)
        h = sha256(p).hexdigest()
        return Path(h[:2], h[2:])

    def fetch(self, key: Any) -> Path | None:
        path = self.get_name(key)
        if path.exists():
            return path
        return None

    def get_name(self, key: Any) -> Path:
        dest = self.directory / self.get_key(key)
        dest.parent.mkdir(exist_ok=True)
        return dest

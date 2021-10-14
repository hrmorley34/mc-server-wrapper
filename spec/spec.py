from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence, TextIO
from .base import YamlObject, load
from .jars import BaseJar, BaseLaunchableJar
from .store import BaseStore


class Specification(YamlObject, yamltag="!spec", path_resolver=[]):
    server: BaseLaunchableJar
    plugins: Sequence[BaseJar]
    store: BaseStore
    folders: FolderSpecification

    def __init__(
        self,
        server: BaseLaunchableJar,
        plugins: Sequence[BaseJar],
        store: BaseStore,
        folders: FolderSpecification,
        **kw: Any,
    ):
        assert isinstance(server, BaseLaunchableJar)
        self.server = server
        assert all(isinstance(p, BaseJar) for p in plugins)
        self.plugins = list(plugins)
        assert isinstance(store, BaseStore)
        self.store = store
        assert isinstance(folders, FolderSpecification)
        self.folders = folders
        print("Specification given extra keys:", kw)

    @classmethod
    def from_yaml(cls, stream: str | TextIO) -> Specification:
        return load(stream)


class FolderSpecification(YamlObject, yamltag="!folder", path_resolver=["folders"]):
    server: Path
    plugins: Path

    def __init__(self, server: str | Path, plugins: str | Path, **kw: Any):
        self.server = Path(server)
        self.plugins = Path(plugins)
        print("Folders given extra keys:", kw)

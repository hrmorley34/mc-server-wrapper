from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any, Sequence
from ..base import YamlObject

if TYPE_CHECKING:
    from ..store import BaseStore


class JarInfo:
    def __init__(self, storekey: Any, path: Path, name: str):
        self.storekey = storekey
        self.name = str(name)
        self.path = Path(path)

    def __repr__(self) -> str:
        return f"JarInfo({self.path}, {self.name})"

    storekey: Any
    path: Path
    name: str


class BaseJar(ABC, YamlObject):
    "Represents an accessor for a Jar file"

    @abstractmethod
    def fetch(self, store: BaseStore, dry: bool = False) -> Sequence[JarInfo]:
        pass


class BaseLaunchableJar(BaseJar):
    "Represents an accessor for a Jar file which can be executed"

    @abstractmethod
    def run(self, path: Path, cwd: Path, dry: bool = False):
        pass


class FileJar(BaseJar, yamltag="!jar.file"):
    "Jar located on the local filesystem"

    path: Path

    def __init__(self, path: str):
        self.path = Path(path)

    def _get_key(self):
        return (type(self).__name__, self.path)

    def _get_path(self, store: BaseStore) -> Path:
        return store.get_name(self._get_key())

    def fetch(self, store: BaseStore, dry: bool = False) -> tuple[JarInfo]:
        if dry:
            return (JarInfo(
                storekey=self._get_key(),
                path=self._get_path(store),
                name=self.path.name,
            ),)
        return (JarInfo(
            storekey=self._get_key(),
            path=shutil.copy2(self.path, self._get_path(store)),
            name=self.path.name,
        ),)


class GlobJar(BaseJar, yamltag="!jar.glob"):
    "Jar(s) located on the local filesystem"

    glob: str
    limit: int | None

    def __init__(self, path: str, limit: int | None = 1):
        if limit is not None and limit < 1:
            raise ValueError("Limit must be None or greater than 0")
        self.glob = str(path)
        self.limit = limit

    def _get_key(self, filename: str) -> tuple[str, str, str]:
        return (type(self).__name__, self.glob, filename)

    def _get_path(self, store: BaseStore, filename: str) -> Path:
        return store.get_name(self._get_key(filename))

    def _copy(self, store: BaseStore, src: Path, dry: bool = False) -> JarInfo:
        key = self._get_key(src.name)
        if dry:
            return JarInfo(
                storekey=key,
                path=store.get_name(key),
                name=src.name,
            )
        return JarInfo(
            storekey=key,
            path=Path(shutil.copy2(src, store.get_name(key))),
            name=src.name,
        )

    def fetch(self, store: BaseStore, dry: bool = False) -> list[JarInfo]:
        gl = Path(".").glob(self.glob)

        if self.limit is None:
            return [self._copy(store, path, dry=dry) for path in gl]

        try:
            paths = [next(gl) for _ in range(self.limit)]
        except StopIteration:
            if dry:
                print(f"Not enough files match the glob {self.glob!r}")
                return []
            else:
                raise ValueError(f"Not enough files match the glob {self.glob!r}")
        try:
            next(gl)
        except StopIteration:
            return [self._copy(store, path, dry=dry) for path in paths]
        else:
            if dry:
                print(f"Not enough files match the glob {self.glob!r}")
                return []
            else:
                raise ValueError(f"Too many files match the glob {self.glob!r}")

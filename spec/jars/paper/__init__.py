from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import time
from typing import TYPE_CHECKING, Mapping, Optional, Sequence
import requests
import subprocess
import sys
from ..base import BaseLaunchableJar, JarInfo
from . import paperflags

if TYPE_CHECKING:
    from ...store import BaseStore


API_ROOT = "https://papermc.io/api/v2"


class BuildInfo(dict):
    @property
    def filename(self) -> str:
        return self["downloads"]["application"]["name"]

    @property
    def url(self) -> str:
        project: str = self["project_id"]
        version: str = self["version"]
        build: int = self["build"]
        return f"{API_ROOT}/projects/{project}/versions/{version}/builds/{build}/downloads/{self.filename}"

    @property
    def timestamp(self) -> datetime:
        return datetime.fromisoformat(str(self["time"]).replace("Z", "+00:00"))


def fetch_version_groups(project: str) -> Sequence[str]:
    r = requests.get(f"{API_ROOT}/projects/{project}")
    r.raise_for_status()
    projdata: Mapping = r.json()
    return projdata.get("version_groups", [])


def fetch_build_by_version_group(project: str, version_group: str) -> BuildInfo:
    r = requests.get(f"{API_ROOT}/projects/{project}/version_group/{version_group}/builds")
    r.raise_for_status()
    buildsdata: Mapping = r.json()
    return BuildInfo(buildsdata["builds"][-1], project_id=project)


def get_latest_version_in_group(project: str, version_group: str) -> BuildInfo:
    version_groups = fetch_version_groups(project)
    if version_group not in version_groups:
        raise ValueError(f"ERROR: cannot find version group {version_group}")
    elif version_group != version_groups[-1]:
        print(f"WARNING: more recent version group found: {version_groups[-1]}", file=sys.stderr)

    return fetch_build_by_version_group(project, version_group)


def download(url: str, dest: Path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


class PaperJar(BaseLaunchableJar, yamltag="!jar.paper"):
    project: str
    version_group: str
    java_bin: str
    java_options: list[str]
    jar_options: list[str]

    def __init__(
        self,
        project: str,
        version_group: str,
        java: str = "java",
        memory: Optional[str] = paperflags._UNSET,
        initial_memory: Optional[str] = paperflags._UNSET,
        aikar_flags: bool = True,
        java_options: Sequence[str] = [],
        options: Optional[Sequence[str]] = None,
    ):
        self.project = str(project)
        self.version_group = str(version_group)  # (in case of accidental float conversion)

        self.java_bin = java
        self.java_options = list(java_options)
        if aikar_flags:
            fl = paperflags.get_flags(memory=memory, init_memory=initial_memory, include_aikar=aikar_flags)
            self.java_options.extend(fl)
        if options is None:
            if self.project == "paper":
                options = ["nogui"]
            else:
                options = []
        self.jar_options = list(options)

    def _get_key(self, url: str):
        return (type(self).__name__, url)

    def fetch(self, store: BaseStore, dry: bool = False) -> tuple[JarInfo]:
        build = get_latest_version_in_group(self.project, self.version_group)
        key = self._get_key(build.url)

        if dry:
            return (JarInfo(
                storekey=key,
                path=store.get_name(key),
                name=build.filename,
            ),)

        p = store.fetch(key)
        if p is not None:
            return (JarInfo(
                storekey=key,
                path=p,
                name=build.filename,
            ),)

        dest = store.get_name(key)

        download(build.url, dest)
        try:
            # set access time to now and set modification time to timestamp (seconds)
            os.utime(dest, (time.time(), build.timestamp.timestamp()))
        except OSError:
            pass
        return (JarInfo(
            storekey=key,
            path=dest,
            name=build.filename,
        ),)

    def build_command(self, jarpath: Path) -> Sequence[str]:
        return [
            self.java_bin,
            *self.java_options,
            "-jar",
            str(jarpath),
            *self.jar_options,
        ]

    def run(self, path: Path, cwd: Path, dry: bool = False):
        cmd = self.build_command(jarpath=path)
        if dry:
            print(cmd)
            return

        subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
        )

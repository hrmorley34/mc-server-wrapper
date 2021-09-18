from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import time
from typing import TYPE_CHECKING, Sequence
import requests
import subprocess
import sys
from ..base import BaseLaunchableJar, JarInfo
from . import paperflags
from .typing import BuildResponse, ProjectId, ProjectResponse, VersionGroup, VersionGroupBuild, VersionGroupBuildsResponse

if TYPE_CHECKING:
    from typing import Literal
    from ...store import BaseStore


API_ROOT = "https://papermc.io/api/v2"


class BuildInfo:
    def __init__(self, response: BuildResponse):
        self.response = response

    @classmethod
    def from_versiongroup(cls, buildsdata: VersionGroupBuildsResponse, build: VersionGroupBuild) -> BuildInfo:
        br = BuildResponse(project_id=buildsdata["project_id"], project_name=buildsdata["project_name"], **build)
        return cls(br)

    response: BuildResponse

    @property
    def filename(self) -> str:
        return self.response["downloads"]["application"]["name"]

    @property
    def url(self) -> str:
        project = self.response["project_id"]
        version = self.response["version"]
        build = self.response["build"]
        return f"{API_ROOT}/projects/{project}/versions/{version}/builds/{build}/downloads/{self.filename}"

    @property
    def timestamp(self) -> datetime:
        return datetime.fromisoformat(str(self.response["time"]).replace("Z", "+00:00"))


def fetch_version_groups(project: ProjectId) -> list[VersionGroup]:
    r = requests.get(f"{API_ROOT}/projects/{project}")
    r.raise_for_status()
    projdata: ProjectResponse = r.json()
    return projdata.get("version_groups", [])


def fetch_build_by_version_group(project: ProjectId, version_group: VersionGroup) -> BuildInfo:
    r = requests.get(f"{API_ROOT}/projects/{project}/version_group/{version_group}/builds")
    r.raise_for_status()
    buildsdata: VersionGroupBuildsResponse = r.json()
    return BuildInfo.from_versiongroup(buildsdata, buildsdata["builds"][-1])


def get_latest_version_in_group(project: ProjectId, version_group: VersionGroup) -> BuildInfo:
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
    project: ProjectId
    version_group: VersionGroup
    java_bin: str
    java_options: list[str]
    jar_options: list[str]

    def __init__(
        self,
        project: str,
        version_group: str,
        java: str = "java",
        memory: str | None | Literal[False] = False,
        initial_memory: str | None | Literal[False] = False,
        aikar_flags: bool = True,
        java_options: Sequence[str] = [],
        options: Sequence[str] | None = None,
    ):
        self.project = ProjectId(project)
        # Cast to str first in case yaml interprets as float
        self.version_group = VersionGroup(str(version_group))

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

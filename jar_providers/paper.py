from datetime import datetime
import os
from pathlib import Path
import time
from typing import Mapping, Sequence, Union
import requests
import sys
from .base import BaseJar, convert_data, err_if_data


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


class PaperJar(BaseJar):
    project: str
    version_group: str

    def __init__(self, data: Union[Mapping, str]):
        data = convert_data(data)

        t = data.pop("type")

        self.project = str(data.pop("project", t))
        self.version_group = str(data.pop("version_group"))

        err_if_data(data, "PaperJar")

    def fetch(self, dest: Path) -> Path:
        build = get_latest_version_in_group(self.project, self.version_group)
        if dest.is_dir():
            dest = dest / build.filename
        download(build.url, dest)
        try:
            # set access time to now and set modification time to timestamp (seconds)
            os.utime(dest, (time.time(), build.timestamp.timestamp()))
        except OSError:
            pass
        return dest


BaseJar.handlers["paper"] = BaseJar.handlers["waterfall"] = PaperJar

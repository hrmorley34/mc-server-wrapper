from __future__ import annotations

from abc import ABC, abstractmethod
import os
from pathlib import Path
import re
import requests
import time
from typing import TYPE_CHECKING, Any, Mapping, MutableSequence, Optional, Sequence, Tuple
from .base import BaseJar, JarInfo
from ..base import YamlObject, YamlScalar

if TYPE_CHECKING:
    from ..store import BaseStore


class _ReturnArtifact:
    def __init__(self, baseurl: str, artifact: Mapping):
        self.artifact = artifact
        self.url = str(baseurl).rstrip("/") + "/artifact/" + artifact["relativePath"]
        self.filename = str(artifact["fileName"])

    artifact: Mapping
    url: str
    filename: str


class Restriction(ABC, YamlObject):
    @abstractmethod
    def check(self, build_data: dict) -> bool:
        """Return true if restrictions match against build data from API

        `build_data` *may* be mutated"""
        pass


class ArtifactGlobRestriction(Restriction, yamltag="!jar.jenkins.r.artifactglob"):
    glob: str

    def __init__(self, glob: str):
        self.glob = str(glob)

    def check(self, build_data: dict) -> bool:
        artifacts: MutableSequence[Mapping[str, str]] = build_data["artifacts"]
        for i, d in reversed(list(enumerate(artifacts))):
            if not Path(d["relativePath"]).match(self.glob):
                artifacts.pop(i)

        return len(artifacts) > 0


class ArtifactFilenameRegexRestriction(Restriction, yamltag="!jar.jenkins.r.artifactregex"):
    pattern: re.Pattern

    def __init__(self, pattern: str):
        self.pattern = re.compile(str(pattern))

    def check(self, build_data: dict) -> bool:
        artifacts: MutableSequence[Mapping[str, str]] = build_data["artifacts"]
        for i, d in reversed(list(enumerate(artifacts))):
            if not self.pattern.fullmatch(d["fileName"]):
                artifacts.pop(i)

        return len(artifacts) > 0


class SuccessRestriction(Restriction, YamlScalar, yamltag="!jar.jenkins.r.success"):
    def check(self, build_data: dict) -> bool:
        return build_data["result"] == "SUCCESS"  # not FAILURE


class ArtifactCountRestriction(Restriction, yamltag="!jar.jenkins.r.artifactcount"):
    min: Optional[int]
    max: Optional[int]

    def __init__(self, number: int = None, min: int = None, max: int = None):
        if number is not None:
            if min is not None or max is not None:
                raise ValueError("Count restriction takes either `number` or `min`/`max`, not both")
            self.min = self.max = number
        else:
            self.min = min
            self.max = max
            if min is None and max is None:
                print("Warning: Count Restriction min and max are both supplied, so it will have no effect")

    def check(self, build_data: dict) -> bool:
        artifacts: MutableSequence[Mapping[str, str]] = build_data["artifacts"]
        count = len(artifacts)
        if self.min is not None and self.min > count:
            return False
        if self.max is not None and self.max < count:
            return False
        return True


class JenkinsBuildJar(BaseJar, yamltag="!jar.jenkins"):
    baseurl: str
    restrictions: list[Restriction]

    def __init__(self, url: str, job: str = None, restrictions: Sequence[Restriction] = []):
        # url can be the CI server with job argument, or the direct job
        self.baseurl = str(url).rstrip("/")
        if job is not None:
            self.baseurl = self.baseurl.rstrip("/") + "/job/" + str(job)

        self.restrictions = list(restrictions)

    def _api_get(self, url: str, tree: Optional[str] = None) -> dict:
        r = requests.get(url.rstrip("/") + "/api/json", params={"tree": tree})
        r.raise_for_status()
        return r.json()

    def fetch_builds_url(self) -> Sequence[str]:
        builds: list[dict[str, str]] = self._api_get(self.baseurl, tree="builds[url]")["builds"]
        return [str(build["url"]) for build in builds]

    def fetch_stable_url(self) -> str:
        return str(self._api_get(self.baseurl, tree="lastStableBuild[url]")["lastStableBuild"]["url"])

    def fetch_latest_filtered_build(self) -> dict[str, Any]:
        if not self.restrictions:
            buildurl = self.fetch_stable_url()
            data = self._api_get(buildurl)
        else:
            for buildurl in self.fetch_builds_url():
                data = self._api_get(buildurl)
                for res in self.restrictions:
                    if not res.check(data):
                        break  # escape restrictions, avoiding else clause (continue to next `buildurl`)
                else:
                    break  # leave with this `buildurl`
            else:
                # if break not triggered in buildurl loop
                raise ValueError("No builds match the required restrictions")
        return data  # data["url"] is buildurl; doesn't need to be returned separately

    def extract_artifact(self, data: dict[str, Any]) -> list[_ReturnArtifact]:
        artifacts: Sequence[Mapping[str, str]] = data["artifacts"]
        return [_ReturnArtifact(data["url"], artifact) for artifact in artifacts]

    def download(self, url: str, dest: Path):
        r = requests.get(url, stream=True)
        r.raise_for_status()

        with open(dest, "wb") as fd:
            for chunk in r.iter_content(chunk_size=4096):
                fd.write(chunk)

    def _store_key(self, url: str) -> Tuple[str, str]:
        return (type(self).__name__, url)

    def fetch(self, store: BaseStore, dry: bool = False) -> list[JarInfo]:
        data = self.fetch_latest_filtered_build()
        artifacts = self.extract_artifact(data)

        ret: list[JarInfo] = []
        for art in artifacts:
            key = self._store_key(art.url)
            if dry:
                ret.append(JarInfo(
                    storekey=key,
                    path=store.get_name(key),
                    name=art.filename,
                ))
                continue

            c = store.fetch(key)
            if c is not None:
                ret.append(JarInfo(
                    storekey=key,
                    path=c,
                    name=art.filename,
                ))
                continue

            dest = store.get_name(key)

            self.download(art.url, dest)

            try:
                # set access time to now and set modification time to timestamp (convert ms -> ns)
                os.utime(dest, ns=(time.time_ns(), data["timestamp"] * 10**6))
            except OSError:
                pass

            ret.append(JarInfo(
                storekey=key,
                path=dest,
                name=art.filename,
            ))

        return ret

from abc import ABC, abstractmethod
import collections.abc
import os
from pathlib import Path
import re
import requests
import time
from typing import Mapping, MutableMapping, MutableSequence, Sequence, Type, Union
from .base import BaseJar, convert_data, err_if_data


class Restriction(ABC):
    handlers: MutableMapping[str, Type["Restriction"]] = {}

    def __new__(cls, data: Union[Mapping, str]) -> "Restriction":
        "If a Restriction is called, create a restriction of the appropriate `data[\"type\"]`"
        if cls is Restriction:  # not on subtype
            if isinstance(data, collections.abc.Mapping):
                t: str = str(data.get("type"))
            else:
                t = data  # a lone name is used as a type without arguments

            if t in cls.handlers:
                return object.__new__(cls.handlers[t])
            else:
                raise ValueError(f"Unknown restriction type: {t}")
        return object.__new__(cls)

    def __init__(self, data: Union[Mapping, str]):
        pass

    @abstractmethod
    def check(self, build_data: dict) -> bool:
        """Return true if restrictions match against build data from API

        `build_data` *may* be mutated"""
        pass


class ArtifactGlobRestriction(Restriction):
    glob: str

    def __init__(self, data: Union[Mapping, str]):
        data = convert_data(data)

        data.pop("type")
        self.glob = str(data.pop("glob"))

        err_if_data(data, "ArtifactGlobRestriction")

    def check(self, build_data: dict) -> bool:
        artifacts: MutableSequence[Mapping[str, str]] = build_data["artifacts"]
        for i, d in reversed(list(enumerate(artifacts))):
            if not Path(d["relativePath"]).match(self.glob):
                artifacts.pop(i)

        return len(artifacts) > 0


Restriction.handlers["glob"] = ArtifactGlobRestriction


class ArtifactFilenameRegexRestriction(Restriction):
    pattern: re.Pattern

    def __init__(self, data: Union[Mapping, str]):
        data = convert_data(data)

        data.pop("type")
        self.pattern = re.compile(str(data.pop("pattern")))

        err_if_data(data, "ArtifactGlobRestriction")

    def check(self, build_data: dict) -> bool:
        artifacts: MutableSequence[Mapping[str, str]] = build_data["artifacts"]
        for i, d in reversed(list(enumerate(artifacts))):
            if not self.pattern.fullmatch(d["fileName"]):
                artifacts.pop(i)

        return len(artifacts) > 0


Restriction.handlers["regex"] = Restriction.handlers["re"] = ArtifactFilenameRegexRestriction


class SuccessRestriction(Restriction):
    pattern: re.Pattern

    def __init__(self, data: Union[Mapping, str]):
        data = convert_data(data)
        data.pop("type")
        err_if_data(data, "SuccessRestriction")

    def check(self, build_data: dict) -> bool:
        return build_data["result"] == "SUCCESS"  # not FAILURE


Restriction.handlers["success"] = Restriction.handlers["successful"] = SuccessRestriction


class JenkinsBuildJar(BaseJar):
    baseurl: str
    restrictions: MutableSequence[Restriction]

    def __init__(self, data: Union[Mapping, str]):
        data = convert_data(data)

        data.pop("type")

        # url can be the CI server with job argument, or the direct job
        self.baseurl = str(data.pop("url")).rstrip("/")
        if data.get("job"):
            self.baseurl = self.baseurl.rstrip("/") + "/job/" + str(data.pop("job"))

        self.restrictions = []
        if data.get("restrictions"):
            self.restrictions.extend(map(Restriction, data.pop("restrictions")))

        err_if_data(data, "JenkinsBuildJar")

    def _api_get(self, url: str, tree: str = None) -> Mapping:
        r = requests.get(url.rstrip("/") + "/api/json", params={"tree": tree})
        r.raise_for_status()
        return r.json()

    def fetch_builds_url(self) -> Sequence[str]:
        builds: list = self._api_get(self.baseurl, tree="builds[url]")["builds"]
        return [str(build["url"]) for build in builds]

    def fetch_stable_url(self) -> str:
        return str(self._api_get(self.baseurl, tree="lastStableBuild[url]")["lastStableBuild"]["url"])

    def fetch_latest_filtered_build(self) -> dict:
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

    def download_artifact(self, data: dict, dest: Path) -> Path:
        artifacts: Sequence[Mapping[str, str]] = data["artifacts"]
        if len(artifacts) > 1:
            raise ValueError("Multiple artifacts given")
        elif len(artifacts) < 1:
            raise ValueError("No artifacts given")
        url = str(data["url"]).rstrip("/") + "/artifact/" + artifacts[0]["relativePath"]

        if dest.is_dir():
            dest = dest / artifacts[0]["fileName"]

        r = requests.get(url, stream=True)
        r.raise_for_status()

        with open(dest, "wb") as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)
        return dest

    def fetch(self, dest: Path) -> Path:
        data = self.fetch_latest_filtered_build()
        dest = self.download_artifact(data, dest)

        try:
            # set access time to now and set modification time to timestamp (convert ms -> ns)
            os.utime(dest, ns=(time.time_ns(), data["timestamp"] * 10**6))
        except OSError:
            pass

        return dest


BaseJar.handlers["jenkins"] = JenkinsBuildJar

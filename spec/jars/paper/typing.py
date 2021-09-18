from __future__ import annotations

from typing import NewType, TypedDict


ProjectId = NewType("ProjectId", str)  # [a-z]+
ProjectName = str
VersionGroup = NewType("VersionGroup", str)  # [0-9pre.-]+
Version = NewType("Version", str)  # [0-9pre.-]+
BuildId = NewType("BuildId", int)  # \d+


class Change(TypedDict):
    commit: str
    summary: str
    message: str


class Download(TypedDict):
    name: str  # [a-z0-9._-]+
    sha256: str  # [a-f0-9]{64}


class VersionGroupBuild(TypedDict):
    build: BuildId
    time: str  # time in format yyyy-mm-ddThh-mm-ss.sssZ
    changes: list[Change]
    downloads: dict[str, Download]
    version: Version  # not mentioned in docs


class ProjectsResponse(TypedDict):
    "/v2/projects"
    projects: list[ProjectId]


class ProjectResponse(TypedDict):
    "/v2/projects/{project}"
    project_id: ProjectId
    project_name: ProjectName
    version_groups: list[VersionGroup]
    versions: list[Version]


class VersionGroupResponse(TypedDict):
    "/v2/projects/{project}/version_group/{versionGroup}"
    project_id: ProjectId
    project_name: ProjectName
    version_group: VersionGroup
    versions: list[Version]


class VersionGroupBuildsResponse(TypedDict):
    "​/v2​/projects​/{project}​/version_group​/{versionGroup}​/builds"
    project_id: ProjectId
    project_name: ProjectName
    version_group: VersionGroup
    versions: list[Version]
    builds: list[VersionGroupBuild]


class VersionResponse(TypedDict):
    "/v2/projects/{project}/versions/{version}"
    project_id: ProjectId
    project_name: ProjectName
    version: Version
    builds: list[BuildId]


class BuildResponse(VersionGroupBuild):
    "​/v2​/projects​/{project}​/versions​/{version}​/builds​/{build}"
    project_id: ProjectId
    project_name: ProjectName
    version: Version
    # and all from VersionGroupBuild

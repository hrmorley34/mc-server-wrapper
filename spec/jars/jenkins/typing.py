from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from typing import Literal


class Artifact(TypedDict):
    displayPath: str
    fileName: str
    relativePath: str


class BuildData(TypedDict):
    actions: list[dict[str, Any]]
    artifacts: list[Artifact]
    building: bool
    description: str | None
    displayName: str
    duration: int | None
    estimatedDuration: int | None
    executor: Any | None
    fullDisplayName: str
    id: str
    keepLog: bool
    number: int
    queueId: int
    result: Literal["SUCCESS", "FAILURE"]
    timestamp: int  # unix milliseconds
    url: str
    changeSet: dict[str, Any]
    culprits: list[dict[str, Any]]


class ShortBuild(TypedDict):
    number: int
    url: str


class JobData(TypedDict):
    actions: list[dict[str, Any]]
    description: str | None
    displayName: str
    displayNameOrNull: str | None
    fullDisplayName: str
    fullName: str
    name: str
    url: str
    buildable: bool
    builds: list[ShortBuild]
    color: str | None
    firstBuild: ShortBuild | None
    healthReport: list[dict[str, Any]]
    inQueue: bool
    keepDependencies: bool
    lastBuild: ShortBuild | None
    lastCompletedBuild: ShortBuild | None
    lastFailedBuild: ShortBuild | None
    lastStableBuild: ShortBuild | None
    lastSuccessfulBuild: ShortBuild | None
    lastUnstableBuild: ShortBuild | None
    lastUnsuccessfulBuild: ShortBuild | None
    nextBuildNumber: int
    property: list[dict[str, Any]]
    queueItem: Any | None
    concurrentBuild: bool
    disabled: bool
    downstreamProjects: list[Any]
    labelExpression: Any | None
    scm: dict[str, Any]
    upstreamProjects: list[Any]

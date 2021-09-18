from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:
    from typing import Literal


def check_memory_flag(memory: str) -> str:
    if not re.match(r"\d+[kmgt]", memory, re.I):
        raise ValueError(f"Invalid memory value: {memory}")
    return memory


def get_aikar_flags() -> Sequence[str]:
    return [
        "-XX:+UseG1GC",
        "-XX:+ParallelRefProcEnabled",
        "-XX:MaxGCPauseMillis=200",
        "-XX:+UnlockExperimentalVMOptions",
        "-XX:+DisableExplicitGC",
        "-XX:+AlwaysPreTouch",
        "-XX:G1NewSizePercent=30",
        "-XX:G1MaxNewSizePercent=40",
        "-XX:G1HeapRegionSize=8M",
        "-XX:G1ReservePercent=20",
        "-XX:G1HeapWastePercent=5",
        "-XX:G1MixedGCCountTarget=4",
        "-XX:InitiatingHeapOccupancyPercent=15",
        "-XX:G1MixedGCLiveThresholdPercent=90",
        "-XX:G1RSetUpdatingPauseTimePercent=5",
        "-XX:SurvivorRatio=32",
        "-XX:+PerfDisableSharedMem",
        "-XX:MaxTenuringThreshold=1",
        "-Dusing.aikars.flags=https://mcflags.emc.gs",
        "-Daikars.new.flags=true",
    ]


def get_flags(
    memory: str | None | Literal[False],
    init_memory: str | None | Literal[False] = False,
    include_aikar: bool = True,
) -> Sequence[str]:
    args: list[str] = []

    if memory is not None and memory is not False:
        memory = check_memory_flag(memory)
        args.append("-Xmx" + memory)
        if init_memory is None:
            init_memory = memory

    if init_memory is not None and init_memory is not False:
        memory = check_memory_flag(init_memory)
        args.append("-Xms" + init_memory)

    if include_aikar:
        args.extend(get_aikar_flags())

    return args


def get_paperclip_command(java: str = "java", jar: str = "paperclip.jar", flags: Mapping[str, Any] = {}) -> Sequence[str]:
    fl = get_flags(**flags)

    return [java, *fl, "-jar", jar, "nogui"]


def get_waterfall_command(java: str = "java", jar: str = "waterfall.jar", flags: Mapping[str, Any] = {}) -> Sequence[str]:
    fl = get_flags(**flags)

    return [java, *fl, "-jar", jar]

from __future__ import annotations

import argparse
from enum import Enum
from pathlib import Path
from shutil import copy2
import sys
from typing import Any, Sequence, TextIO

from .parser import DownloadAction, parse_args
from .. import jars  # noqa: F401
from ..spec import Specification


def copy_file(src: Path, dest: Path):
    return copy2(src, dest)


def copy_dry(src: Path, dest: Path):
    print(f"Copying {src} to {dest}")


def clear_dir(dir: Path):
    for f in dir.glob("*.jar"):
        f.unlink()
        print(f"Deleted old {f}")


def clear_dry(dir: Path):
    print(f"Clearing {dir}/*.jar")


def main(argv: Sequence[str] | None = None):
    args = parse_args(argv)

    with args.specification as f:
        spec = Specification.from_yaml(f)

    DRY = args.dry

    serverdest = None
    if args.download:
        copy = copy_dry if DRY else copy_file
        clear = clear_dry if DRY else clear_dir

        copyops: list[tuple[Path, Path]] = []

        print(f"Downloading server {spec.server}")
        for ji in spec.server.fetch(spec.store, dry=DRY):
            serverdest = spec.folders.server / ji.name
            copyops.append((ji.path, serverdest))
        assert serverdest is not None

        for pl in spec.plugins:
            print(f"Downloading plugin {pl}")
            for ji in pl.fetch(spec.store, dry=DRY):
                copyops.append((ji.path, spec.folders.plugins / ji.name))

        if args.download != DownloadAction.DownloadOnly:
            if not DRY:
                spec.folders.server.mkdir(parents=True, exist_ok=True)
                spec.folders.plugins.mkdir(parents=True, exist_ok=True)
            clear(spec.folders.server)
            clear(spec.folders.plugins)
            print("Copying files to destination")
            for src, dest in copyops:
                copy(src, dest)

    if args.run:
        assert serverdest is not None
        print(f"Running server {serverdest}")

        sys.stdout.flush()  # ready to pass over to subprocess
        sys.stderr.flush()

        spec.server.run(serverdest, cwd=spec.folders.server, dry=DRY)

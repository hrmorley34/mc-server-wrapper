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


def main(argv: Sequence[str] | None = None):
    args = parse_args(argv)

    with args.specification as f:
        spec = Specification.from_yaml(f)

    DRY = args.dry

    serverdest = None
    if args.download:
        copy = copy_dry if DRY else copy_file

        if not DRY:
            spec.folders.server.mkdir(parents=True, exist_ok=True)
        print(f"Downloading server {spec.server}")
        for ji in spec.server.fetch(spec.store, dry=DRY):
            serverdest = spec.folders.server / ji.name
            if args.download != DownloadAction.DownloadOnly:
                copy(ji.path, serverdest)
        assert serverdest is not None

        if not DRY:
            spec.folders.plugins.mkdir(parents=True, exist_ok=True)
        for pl in spec.plugins:
            print(f"Downloading plugin {pl}")
            for ji in pl.fetch(spec.store, dry=DRY):
                if args.download != DownloadAction.DownloadOnly:
                    copy(ji.path, spec.folders.plugins / ji.name)

    if args.run:
        assert serverdest is not None
        print(f"Running server {serverdest}")

        sys.stdout.flush()  # ready to pass over to subprocess
        sys.stderr.flush()

        spec.server.run(serverdest, cwd=spec.folders.server, dry=DRY)

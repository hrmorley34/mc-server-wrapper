from __future__ import annotations

import argparse
from pathlib import Path
from shutil import copy2
from typing import Sequence, TextIO
from . import jars  # noqa: F401
from .spec import Specification


def copy_file(src: Path, dest: Path):
    return copy2(src, dest)


def copy_dry(src: Path, dest: Path):
    print(f"Copying {src} to {dest}")


def add_yesno_args(
    p: argparse.ArgumentParser,
    *names: str,
    truenames: Sequence[str] = [],
    falsenames: Sequence[str] = [],
    required: bool = False,
    dest: str | None = None,
    **kwargs,
) -> argparse._MutuallyExclusiveGroup:
    yesnames = list(names) + list(truenames)
    nonames = [name.replace("--", "--no-") for name in names if name.startswith("--")]
    nonames += list(falsenames)

    mut = p.add_mutually_exclusive_group(required=required)

    ykwargs = kwargs.copy()
    if dest is not None:
        ykwargs["dest"] = dest
    yarg = mut.add_argument(*yesnames, action="store_true", **ykwargs)

    nkwargs = kwargs.copy()
    nkwargs["dest"] = yarg.dest
    mut.add_argument(*nonames, action="store_false", **nkwargs)

    return mut


parser = argparse.ArgumentParser()
add_yesno_args(parser, "-l", "--list")
add_yesno_args(parser, "--dl", "--download", required=True)
add_yesno_args(parser, "-r", "--run", default=False)
parser.add_argument("specification", type=argparse.FileType("r"))
parser.add_argument("-d", "--dry", action="store_true",
                    help="Do not download anything; just show what would happen")
parser.add_argument("-f", "--force", action="store_true",
                    help="Clear cache and re-download everything")


def main(argv: Sequence[str] | None = None):
    args = parser.parse_args(argv)

    with args.specification as f:
        f: TextIO
        spec = Specification.from_yaml(f)

    DRY: bool = args.dry

    if args.download:
        copy = copy_dry if DRY else copy_file

        if not DRY:
            spec.folders.server.mkdir(parents=True, exist_ok=True)
        serverdest = None
        for ji in spec.server.fetch(spec.store, dry=True):
            serverdest = spec.folders.server / ji.name
            copy(ji.path, serverdest)
        assert serverdest is not None

        if not DRY:
            spec.folders.plugins.mkdir(parents=True, exist_ok=True)
        for pl in spec.plugins:
            for ji in pl.fetch(spec.store, dry=True):
                copy(ji.path, spec.folders.plugins / ji.name)

    if args.run:
        spec.server.run(serverdest, cwd=Path.cwd(), dry=DRY)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from enum import Enum
from typing import Sequence, TextIO


class BoolEnum(Enum):
    def __bool__(self):
        return self.value > 0


class DownloadAction(BoolEnum):
    NoDownload = 0
    Download = 1
    DownloadOnly = 2


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument("-l", "--list", dest="list", action="store_true",
                        help="List all plugins")

    dlpars = parser.add_mutually_exclusive_group(required=True)
    dlpars.add_argument("--dl", "--download", dest="download", action="store_const", const=DownloadAction.Download,
                        help="Download plugins and replace them")
    dlpars.add_argument("--dl-only", "--download-only", dest="download", action="store_const", const=DownloadAction.DownloadOnly,
                        help="Download plugins, but do not copy (this will cache them)")
    dlpars.add_argument("--no-dl", "--no-download", dest="download", action="store_const", const=DownloadAction.NoDownload,
                        help="Do not download updated plugins")

    parser.add_argument("-r", "--run", dest="run", action="store_true",
                        help="Run the server")

    parser.add_argument("specification", type=argparse.FileType("r"),
                        help="The server definition file")

    parser.add_argument("-d", "--dry", dest="dry", action="store_true",
                        help="Do not download anything; just show what would happen")
    parser.add_argument("-f", "--force", dest="force", action="store_true",
                        help="Clear cache and re-download everything")

    return parser


class ArgNamespace(argparse.Namespace):
    list: bool
    download: DownloadAction
    run: bool
    specification: TextIO
    dry: bool
    force: bool


def parse_args(args: Sequence[str] | None = None) -> ArgNamespace:
    return create_parser().parse_args(args, namespace=ArgNamespace())

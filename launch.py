import argparse
from jar_providers.cache import NoCache
from pathlib import Path
from typing import TextIO

from flags import get_paperclip_command, get_waterfall_command
from specs import Specification


parser = argparse.ArgumentParser()
parser.add_argument("specification", type=argparse.FileType("r"))


def main(argv=None):
    args = parser.parse_args(argv)

    with args.specification as f:
        f: TextIO
        spec = Specification.from_yaml(f)

    cache = NoCache()

    print(spec.server.fetch(Path("test/paperclip.jar"), cache))
    for pl in spec.plugins:
        print(pl.fetch(Path("test/plugins/"), cache))

    spec.server.


if __name__ == "__main__":
    main()

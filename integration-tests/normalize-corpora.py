#!/bin/env python3

import asyncio
import re
from functools import partial
from pathlib import Path
from typing import Final
from sys import argv

import tqdm

from utils import indicate_progress

CORPORA_PATH: Final = Path(__file__).parent.resolve() / "corpora"

# the casebooks corpus uses an external, local .dtd file whose reference needs to be
# adjusted

adjust_casebooks_dtd_path = partial(
    re.compile(re.escape(b"../schema/entities.dtd"), flags=re.IGNORECASE).subn,
    b"./entities.dtd",
)


# the papyri corpus contains CR entities (&#xD;) that are implicitly converted to LF
# characters on serialization and that is okay. for example:
#
# <change when="2019-02-26T04:28:22-05:00"
#                  who="http://papyri.info/users/WesselvanDuijn">Submit - Submitted&#xD;
# </change>
#
# it seems to appear in editorial notes only and thus these entities have presumably
# been produced by an editor on Windows OS.

cr_ent_to_lf = partial(re.compile(re.escape(b"&#xd;"), flags=re.IGNORECASE).subn, b"\n")


async def normalize_file(file: Path, indicate: callable = indicate_progress):
    match file.parent.name:
        case "casebooks":
            contents, subs = adjust_casebooks_dtd_path(file.read_bytes())
        case "papyri":
            contents, subs = cr_ent_to_lf(file.read_bytes())
        case _:
            indicate()
            return

    if subs:
        file.write_bytes(contents)
    indicate()


async def main():
    root = CORPORA_PATH
    if len(argv) > 1:
        root /= argv[1]
    print(f"Normalizing contents of {root}")
    files = list(root.rglob("*.xml"))
    pbar = tqdm.tqdm(total=len(files), mininterval=.5)
    async with asyncio.TaskGroup() as tasks:
        for file in files:
            tasks.create_task(normalize_file(file, pbar.update))


if __name__ == "__main__":
    asyncio.run(main())

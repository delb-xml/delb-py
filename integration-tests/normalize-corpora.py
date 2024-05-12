#!/bin/env python3

import asyncio
import re
from functools import partial
from pathlib import Path
from typing import Final
from sys import argv

from tqdm import tqdm

CORPORA_PATH: Final = Path(__file__).parent.resolve() / "corpora"
RELEVANT_CORPORA: Final = ("casebooks", "papyri")

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


async def normalize_file(file: Path, indicate_progress: callable):
    match file.parent.name:
        case "casebooks":
            contents, subs = adjust_casebooks_dtd_path(file.read_bytes())
        case "papyri":
            contents, subs = cr_ent_to_lf(file.read_bytes())
        case _:
            raise RuntimeError

    if subs:
        file.write_bytes(contents)
    indicate_progress()


async def main():
    corpora = [x for x in RELEVANT_CORPORA if x in argv[1:]] or RELEVANT_CORPORA
    for folder in (CORPORA_PATH / x for x in corpora):
        print(f"Normalizing contents of {folder}")
        files = tuple(folder.glob("*.xml"))
        progressbar = tqdm(total=len(files), mininterval=0.5, unit_scale=True)
        async with asyncio.TaskGroup() as tasks:
            for file in files:
                tasks.create_task(normalize_file(file, progressbar.update))
        progressbar.close()


if __name__ == "__main__":
    asyncio.run(main())

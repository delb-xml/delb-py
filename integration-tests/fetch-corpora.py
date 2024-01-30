#!/bin/env python3

# not yet included
#
# XML file with references to files:
# https://sturm-edition.de/api/files/
# flat crawl:
# https://celt.ucc.ie/publishd.html
# deep crawlin':
# https://gams.uni-graz.at/archive/objects/container:mws-gesamt/methods/sdef:Context/get?locale=fr&mode=&context=

# Python 3.12 is required, but sys isn't imported yet

import asyncio
import io
import os
import tarfile
from pathlib import Path
from tempfile import TemporaryFile
from typing import Final, NamedTuple

from httpx import AsyncClient, HTTPError

import delb


# constants


class Archive(NamedTuple):
    url: str
    archive_documents_root: str
    target_directory: str
    extra_files: dict[str, str] = {}


CORPORA_PATH: Final = Path(__file__).parent.resolve() / "corpora"


ARCHIVE_DESCRIPTIONS: Final = (
    Archive(
        url="https://github.com/Brown-University-Library/atalanta-texts/archive/master.tar.gz",
        archive_documents_root="atalanta-texts-master/",
        target_directory="atalanta",
    ),
    Archive(
        # all textual content is encoded w/o linefeeds
        # external DTDs for entities are used
        url="https://github.com/funkyfuture/casebooks-data/archive/master.tar.gz",
        # TODO use this URL when https://github.com/CasebooksProject/casebooks-data/pull/1
        # was merged:
        # url="https://github.com/CasebooksProject/casebooks-data/archive/master.tar.gz",
        archive_documents_root="casebooks-data-master/cases/",
        target_directory="casebooks",
        extra_files={"casebooks-data-master/schema/entities.dtd": "entities.dtd"},
    ),
    Archive(
        url="https://github.com/pruizf/disco/archive/main.tar.gz",
        archive_documents_root="disco-main/tei/all-periods-per-author/",
        target_directory="DISCO",
    ),
    Archive(  # mixed bag of XML encodings, .svg are ignored though
        url="https://github.com/faustedition/faust-xml/archive/master.tar.gz",
        archive_documents_root="faust-xml-master/xml/",
        target_directory="faust-edition",
    ),
    Archive(
        url="https://github.com/bodleian/medieval-mss/archive/master.tar.gz",
        archive_documents_root="medieval-mss-master/collections/",
        target_directory="medieval-manuscripts",
    ),
    Archive(
        # contains Arabic transcriptions
        url="https://github.com/funkyfuture/idp.data/archive/master.tar.gz",
        # TODO use this URL when https://github.com/papyri/idp.data/pull/391
        # was merged:
        # url="https://github.com/papyri/idp.data/archive/master.tar.gz",
        archive_documents_root="idp.data-master/",
        target_directory="papyri",
    ),
    Archive(
        url="https://github.com/i-d-e/ride/archive/master.tar.gz",
        archive_documents_root="ride-master/tei_all/",
        target_directory="ride-reviews",
    ),
)

SKIP_EXISTING: Final = bool(os.environ.get("SKIP_EXISTING", ""))


# helper


http_client: Final = AsyncClient()


async def fetch_resource(url: str, destination: io.BufferedWriter) -> bool:
    async with http_client.stream("GET", url, follow_redirects=True) as response:
        try:
            async for chunk in response.aiter_bytes():
                destination.write(chunk)
        except HTTPError as e:
            print(f"Failed to fetch {url}: {e}")
            return False
        else:
            print(f"Downloaded {url} to {destination.name}")
            return True


def make_archive_filter(archive_description: Archive) -> callable:
    def _filter(member: tarfile.TarInfo, path: str) -> tarfile.TarInfo | None:
        member = tarfile.data_filter(member, path)
        if member is None:
            return None

        member_path = member.name
        root_folder = archive_description.archive_documents_root
        if member_path.endswith(".xml") and member_path.startswith(root_folder):
            return member.replace(
                # the flattening is supposed to destroy Windows OS based environments
                # otherwise it's just neat, not necessary
                name=" ▸ ".join(Path(member_path).relative_to(root_folder).parts)
            )

        extra_files = archive_description.extra_files
        if member_path in extra_files:
            return member.replace(name=extra_files[member_path])

        return None

    return _filter


# there's no business like business


async def fetch_archive(archive_description: Archive):
    target_folder = CORPORA_PATH / archive_description.target_directory
    if SKIP_EXISTING and target_folder.exists():
        return
    target_folder.mkdir(exist_ok=True)

    with TemporaryFile(suffix=".tar.gz") as archive_file:
        await fetch_resource(archive_description.url, archive_file)
        archive_file.seek(0)
        tarfile.open(fileobj=archive_file, mode="r:gz").extractall(
            path=target_folder,
            filter=make_archive_filter(archive_description),
        )
        print(f"Extracted {archive_file.name} to {target_folder}")


async def fetch_sturm_edition():
    base_url = "https://sturm-edition.de/api/files/"
    target_folder = CORPORA_PATH / "sturm-edition"
    if SKIP_EXISTING and target_folder.exists():
        return
    target_folder.mkdir(exist_ok=True)

    for item in delb.Document(base_url).css_select("idno"):
        filename = item.full_text
        if filename in ("Q.01.19151120.JVH.01.xml", "Q.01.19150315.JVH.01.xml"):
            # these are empty files
            continue
        with (target_folder / filename).open("wb") as f:
            await fetch_resource(base_url + filename, f)

    print(f"Fetched all files referenced in {base_url}")


# cli


async def main():
    CORPORA_PATH.mkdir(exist_ok=True)
    async with asyncio.TaskGroup() as tasks:
        for archive_description in ARCHIVE_DESCRIPTIONS:
            tasks.create_task(fetch_archive(archive_description))
        tasks.create_task(fetch_sturm_edition())
    await http_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())

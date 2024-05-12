#!/bin/env python3

from __future__ import annotations

import multiprocessing as mp
import random
from itertools import batched, chain
from pathlib import Path
from typing import TYPE_CHECKING, Final

from tqdm import tqdm

from _delb.plugins.core_loaders import path_loader
from delb import is_tag_node, Document, FailedDocumentLoading, ParserOptions

if TYPE_CHECKING:
    from collections.abc import Iterable

BATCH_SIZE: Final = 64
CPU_COUNT: Final = mp.cpu_count()

CORPORA_PATH: Final = Path(__file__).parent.resolve() / "corpora"

DOCUMENT_SAMPLES_PERCENT: Final = 25
LOCATIONS_PATHS_SAMPLES_PERCENT: Final = 25


def verify_location_paths(file: Path):
    try:
        document = Document(
            file,
            parser_options=ParserOptions(
                collapse_whitespace=False, resolve_entities=False, unplugged=True
            ),
        )
    except FailedDocumentLoading as exc:
        print(
            f"\nFailed to load {file.name}: {exc.excuses[path_loader]}",
            end="",
        )
        return

    root = document.root
    for node in chain((root,), root.iterate_descendants(is_tag_node)):
        if random.randint(1, 100) > LOCATIONS_PATHS_SAMPLES_PERCENT:
            continue

        query_results = document.xpath(node.location_path)
        if not (query_results.size == 1 and query_results.first is node):
            print(
                f"\nXPath query `{node.location_path}` in {file} yielded unexpected "
                "results."
            )


def dispatch_batch(files: Iterable[Path]):
    for file in files:
        try:
            verify_location_paths(file)
        except Exception as e:
            print(f"\nUnhandled exception while testing {file}: {e}")


def main():
    mp.set_start_method("forkserver")

    all_files = tuple(CORPORA_PATH.rglob("*.xml"))
    all_files_size = len(all_files)
    sample_size = int(all_files_size / 100 * DOCUMENT_SAMPLES_PERCENT)
    selected_files = random.choices(all_files, k=sample_size)
    del all_files

    dispatched_tasks = []
    progressbar = tqdm(total=sample_size, mininterval=0.5, unit_scale=True)

    with mp.Pool(CPU_COUNT) as pool:
        for batch in batched(selected_files, n=BATCH_SIZE):
            dispatched_tasks.append(pool.apply_async(dispatch_batch, (batch,)))
            while len(dispatched_tasks) >= CPU_COUNT:
                for task in (t for t in dispatched_tasks if t.ready()):
                    dispatched_tasks.remove(task)
                    progressbar.update(n=BATCH_SIZE)

    print(
        f"\n\nTested against {sample_size} *randomly* selected out of {all_files_size} "
        f"documents."
        f"\n{LOCATIONS_PATHS_SAMPLES_PERCENT}% of the tag nodes' `location_path` "
        f"attribute were verified per document."
    )


if __name__ == "__main__":
    main()

#!/bin/env python3

import multiprocessing as mp
import random
from collections.abc import Iterable
from itertools import chain
from pathlib import Path
from sys import stderr
from typing import Final

from _delb.plugins.core_loaders import path_loader
from delb import is_tag_node, Document, FailedDocumentLoading, ParserOptions

from utils import indicate_progress

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
        if query_results.size == 1 and query_results.first is node:
            indicate_progress()
        else:
            print(
                f"\nXPath query `{node.location_path}` in {file} yielded unexpected "
                "results."
            )
            stderr.write("🕱")


def dispatch_batch(files: Iterable[Path]):
    for file in files:
        try:
            verify_location_paths(file)
        except Exception as e:
            print(f"\nUnhandled exception while testing {file}: {e}")


def main():
    mp.set_start_method("forkserver")

    all_counter = counter = 0
    selected_files = []
    dispatched_tasks = []

    with mp.Pool(CPU_COUNT) as pool:
        for file in CORPORA_PATH.rglob("*.xml"):
            all_counter += 1
            if random.randint(1, 100) > DOCUMENT_SAMPLES_PERCENT:
                continue

            selected_files.append(file)
            counter += 1
            if len(selected_files) < BATCH_SIZE:
                continue

            dispatched_tasks.append(
                pool.apply_async(dispatch_batch, (tuple(selected_files),))
            )
            selected_files.clear()

            while len(dispatched_tasks) >= CPU_COUNT:
                for task in dispatched_tasks:
                    if task.ready():
                        dispatched_tasks.remove(task)

            stderr.flush()

    dispatch_batch(selected_files)
    stderr.flush()

    print(
        f"\n\nTested against {counter} *randomly* selected out of {all_counter} "
        "documents."
        f"\n{LOCATIONS_PATHS_SAMPLES_PERCENT}% of the tag nodes' `location_path` "
        f"attribute were verified per document."
    )


if __name__ == "__main__":
    main()

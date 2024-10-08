#!/bin/env python3

import multiprocessing as mp
from itertools import batched
from pathlib import Path
from sys import stdout
from traceback import print_exception
from typing import Final

from tqdm import tqdm

from _delb.plugins.core_loaders import path_loader
from delb import compare_trees, Document, FailedDocumentLoading, ParserOptions


BATCH_SIZE: Final = 64
CPU_COUNT: Final = mp.cpu_count()

CORPORA_PATH: Final = Path(__file__).parent.resolve() / "corpora"

RESULTS_PATH: Final = (
    Path(__file__).parent.resolve() / "results" / "parsing_and_serializing"
)


def parse_serialize_compare(file: Path):
    result_file = RESULTS_PATH / file.relative_to(CORPORA_PATH)
    result_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        document = Document(
            file,
            parser_options=ParserOptions(reduce_whitespace=False, unplugged=True),
        )
    except FailedDocumentLoading as exc:
        print(f"Failed to load {file.name}: {exc.excuses[path_loader]}")
        return

    try:
        document.save(result_file, indentation="", text_width=0)
    except Exception as e:
        print(f"Failed to save {file.name}:")
        print_exception(e, file=stdout)
        return

    try:
        result_document = Document(result_file)
    except Exception as e:
        print(f"Failed loading re-serialized {file.name}:")
        print_exception(e, file=stdout)
        return

    if (
        document.head_nodes != result_document.head_nodes
        or document.tail_nodes != document.tail_nodes
        or not (difference := compare_trees(document.root, result_document.root))
    ):
        print(f"Unequal document produced from {file.name}:")
        print(difference)
    # TODO? compare with lxml as well
    else:
        result_file.unlink()


def dispatch_batch(files_list: list[Path]):
    for file in files_list:
        try:
            parse_serialize_compare(file)
        except Exception as e:
            print(f"Unhandled exception while testing {file}:")
            print_exception(e, file=stdout)


def main():
    mp.set_start_method("forkserver")

    all_files = tuple(CORPORA_PATH.rglob("*.xml"))
    dispatched_tasks = []
    progressbar = tqdm(total=len(all_files), mininterval=0.5, unit_scale=True)

    with mp.Pool(CPU_COUNT) as pool:
        for file_list in batched(all_files, n=BATCH_SIZE):
            dispatched_tasks.append(
                pool.apply_async(
                    dispatch_batch,
                    (file_list,),
                )
            )

            while len(dispatched_tasks) >= CPU_COUNT:
                for task in (t for t in dispatched_tasks if t.ready()):
                    dispatched_tasks.remove(task)
                    progressbar.update(n=BATCH_SIZE)

    print(f"\nTested against {len(all_files)} documents.")


if __name__ == "__main__":
    main()

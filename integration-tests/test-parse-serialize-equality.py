#!/bin/env python3

from __future__ import annotations

import argparse
import multiprocessing as mp
from fs.memoryfs import MemoryFS
from fs.osfs import OSFS
from os import sync as sync_disk
from pathlib import Path
from random import randrange
from sys import stdout
from traceback import print_exception
from typing import TYPE_CHECKING, Final, Iterable, Iterator, Optional

from tqdm import tqdm

from _delb.plugins.core_loaders import path_loader
from delb import (
    compare_trees,
    Document,
    FailedDocumentLoading,
    ParserOptions,
    PrettyFormatOptions,
)


if TYPE_CHECKING:
    from fs.base import FS

# yes this should be a cli option
CORPORA_PATH: Final = Path(__file__).parent.resolve() / "corpora"


def load_file(filesystem: FS, path: Path, **options) -> Optional[Document]:
    try:
        with filesystem.open(str(path), mode="rb") as f:
            return Document(f, **options)
    except FailedDocumentLoading as e:
        print(f"Failed to load {path.name}: {e.excuses[path_loader]}")
        return None


def save_file(document: Document, filesystem: FS, path: Path, **options) -> bool:
    try:
        with filesystem.open(str(path), mode="wb") as f:
            document.write(f, **options)
    except Exception as e:
        print(f"Failed to save {path.name}:")
        print_exception(e, file=stdout)
        return False
    else:
        return True


def save_and_compare_file(
    origin: Document,
    work_fs: MemoryFS,
    result_file: Path,
    pretty_format_options: None | PrettyFormatOptions,
    reduce_whitespace: bool,
):
    if not save_file(
        origin, work_fs, result_file, pretty_format_options=pretty_format_options
    ):
        return

    if (
        copy_ := load_file(
            work_fs,
            result_file,
            parser_options=ParserOptions(
                reduce_whitespace=reduce_whitespace, unplugged=True
            ),
        )
    ) is None:
        return

    if comparison_result := compare_trees(origin.root, copy_.root):
        work_fs.remove(str(result_file))
    else:
        print(f"Unequal document produced: {result_file}\n{comparison_result}")


def parse_and_serialize_and_compare(src_fs: OSFS, work_fs: MemoryFS, file: Path):
    # unaltered whitespace

    if (
        origin := load_file(
            src_fs,
            file,
            parser_options=ParserOptions(reduce_whitespace=False, unplugged=True),
        )
    ) is None:
        return

    result_file = file.with_stem(f"{file.stem}-plain")
    work_fs.makedirs(str(result_file.parent), recreate=True)
    save_and_compare_file(origin, work_fs, result_file, None, False)

    # altered whitespace

    origin.reduce_whitespace()

    save_and_compare_file(
        origin,
        work_fs,
        file.with_stem(f"{file.stem}-tabbed"),
        PrettyFormatOptions(align_attributes=False, indentation="\t", text_width=0),
        True,
    )

    save_and_compare_file(
        origin,
        work_fs,
        file.with_stem(f"{file.stem}-wrapped"),
        PrettyFormatOptions(align_attributes=False, indentation="  ", text_width=77),
        True,
    )


#


def dispatch_batch(files_list: Iterable[Path], results_folder: Path):
    work_fs = MemoryFS()
    for file in files_list:
        try:
            parse_and_serialize_and_compare(
                OSFS(str(CORPORA_PATH)),
                work_fs,
                file.relative_to(CORPORA_PATH),
            )
        except Exception as e:
            print(f"Unhandled exception while testing {file}:")
            print_exception(e, file=stdout)

    stdout.flush()

    for file in work_fs.glob("**/*.xml"):
        target = results_folder / file.path[1:]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(work_fs.readbytes(file.path))

    sync_disk()


def random_batch(all_files: list[Path], size: int) -> Iterator[Iterable[Path]]:
    # this distributes memory usage over batches as the name sorted file list have some
    # clusters with large files
    # also the progressbar behaves less stucky
    batch: list[Path] = []
    while all_files:
        batch.append(all_files.pop(randrange(len(all_files))))
        if len(batch) == size:
            yield tuple(batch)
            batch.clear()

    if batch:
        yield tuple(batch)


#


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--batch-size", type=int, default=128)
    parser.add_argument("--cpus", type=int, default=2 * mp.cpu_count() - 1)
    parser.add_argument(  # using a ramdisk for this is recommended
        "-r", "--results-path", type=Path, default=CORPORA_PATH.parent / "results"
    )
    return parser.parse_args()


def main():
    mp.set_start_method("forkserver")

    args = parse_args()

    results_path: Final = args.results_path / "parsing_and_serializing"
    all_files: Final = list(CORPORA_PATH.rglob("*.xml"))
    all_files_size: Final = len(all_files)
    dispatched_tasks = []
    progressbar = tqdm(total=all_files_size, mininterval=0.5, unit_scale=True)

    with mp.Pool(args.cpus) as pool:
        for file_batch in random_batch(all_files, args.batch_size):
            dispatched_tasks.append(
                pool.apply_async(
                    dispatch_batch,
                    (file_batch, results_path),
                )
            )

            while len(dispatched_tasks) >= args.cpus:
                for task in (t for t in dispatched_tasks if t.ready()):
                    dispatched_tasks.remove(task)
                    progressbar.update(n=args.batch_size)

    print(f"\nTested against {all_files_size} documents.")

    for path, directories, files in results_path.walk(top_down=False):
        if len(directories) + len(files) == 0:
            path.rmdir()


if __name__ == "__main__":
    main()

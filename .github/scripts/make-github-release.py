import os
import re
import subprocess
import sys
from pathlib import Path

from pypandoc import convert_text, download_pandoc


CWD = Path().cwd()


date_pattern = r"\(\d\d\d\d-\d\d-\d\d\)"
version_pattern = r"\d+\.\d+(\.\d+)?-?(rc\d+)?"

matches_version_header = re.compile(rf"^{version_pattern} {date_pattern}$").match


def extract_relevant_contents(expected_version: str) -> str:
    # This isn't solved with a pandoc filter as pandoc only recognizes the level 3
    # headers as such.

    line_feed = iter((CWD / "CHANGES.rst").read_text().splitlines())

    while True:
        line = next(line_feed)
        if matches_version_header(line) and line.startswith(expected_version):
            break

    assert next(line_feed)[0] == "-"
    assert next(line_feed) == ""

    lines: list[str] = []
    while not matches_version_header(line := next(line_feed)):
        lines.append(line)

    while lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def make_github_release(notes: str, version: str):
    options = []
    options.extend(["--notes-file", "-"])
    options.extend(["--title", f"delb {version}"])
    options.append("--verify-tag")
    if "rc" in version:
        options.append("--prerelease")

    result = subprocess.run(
        [
            "gh",
            "release",
            "create",
        ]
        + options
        + [version],
        capture_output=True,
        encoding="utf-8",
        input=notes,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stdout)
    result.check_returncode()


def make_release_notes(version: str) -> str:
    os.environ["DELB_DOCS_BASE_URL"] = f"https://delb.readthedocs.io/{version}/"
    return (
        convert_text(
            extract_relevant_contents(version),
            format="rst",
            to="markdown_strict",
            extra_args=["--shift-heading-level-by=1", "--wrap=none"],
            filters=[".github/scripts/release-notes-pandoc-filter.py"],
        )
        + "\n\n----\n\nThe package distributions are available at the "
        + f"[Python Package Index](https://pypi.org/project/delb/)."
    )


def main(version: str):
    download_pandoc()
    make_github_release(notes=make_release_notes(version), version=version)


if __name__ == "__main__":
    main(sys.argv[1])

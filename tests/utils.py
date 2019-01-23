import re
from collections import Counter

from xmldiff import main as xmldiff


find_processing_instructions = re.compile(r"(<\?\w\S*?(\s.*?)?\?>)").findall


def assert_documents_are_semantical_equal(old, new):
    changes = xmldiff.diff_files(
        str(old), str(new), diff_options={"F": 1.0, "ratio_mode": "accurate"}
    )
    assert not changes, changes


def count_pis(source):
    with source.open("rt") as f:
        pi_strings = find_processing_instructions(f.read())
    return Counter(x[0] for x in pi_strings if not x[0].startswith("<?xml"))

from __future__ import annotations

from fnmatch import fnmatch
from multiprocessing import Process
from pathlib import Path
from typing import NamedTuple

import pytest
from lxml import etree

from delb import Document, FailedDocumentLoading
from _delb.parser import ParserOptions
from _delb.plugins import plugin_manager
from _delb.plugins.core_loaders import path_loader

from tests.utils import skip_long_running_test


pytestmark = skip_long_running_test


class W3CConformanceTest(NamedTuple):
    parser: str
    path: Path
    entities: str
    id: str
    sections: str
    type: str


ACTUALLY_VALID_CASES = {
    # must fail when these encodings aren't supported. they are.
    "pr-xml-euc-jp",
    "pr-xml-iso-2022-jp",
    "pr-xml-shift_jis",
    # it's unclear what's supposed to be wrong with these.
    "utf16b",
    "utf16l",
}


IGNORED_SECTIONS = {
    # dealing with elaborated / invalid DTDs and DTD validation are no project goals
    "2.9",
    "3.2.2",
    "3.3.1",
    "3.3.2",
    "3.4",
    # the test suite relates to the 4th edition and in the 5th this reference of
    # character classes is obsolete.
    "B.",
}


# TODO generate documentation appendix from this?
IGNORED_TESTS = {
    #
    # the notation is glob pattern (evaluated w/ fnmatch)
    #
    None: {
        # dealing with elaborated DTDs isn't a project goal. these cases use invalid
        # ones, yet the document itself is parseable.
        "o-p11pass1",
        # this considers ':' to be a valid attribute name
        "valid-sa-012",
        # lxml explicitly about element names like 'A.-:̀·', likely also the case for
        # expat
        "o-p0[45]pass1",
    },
    "expat": {
        # dealing with elaborated DTDs isn't a project goal. these cases use invalid
        # ones, yet the document itself is parseable.
        "ibm-invalid-P68-ibm68i0?.xml",
        "ibm-not-wf-P69-ibm69n05.xml",
        "ibm-not-wf-P77-ibm77n0[34].xml",
        # the entity resolver is never called
        "uri01",
    },
    "lxml": {
        # dealing with elaborated DTDs isn't a project goal. these cases use invalid
        # ones, yet the document itself is parseable.
        "ibm-invalid-P69-ibm69i0?.xml",
        "not-wf-not-sa-005",
        # these are valid DTD uses that lxml fails.
        "ext01",
        # it's unclear why these *crash*.
        "ibm-valid-P09-ibm09v0[35].xml",
        "ibm-valid-P11-ibm11v0[34].xml",
        "ibm-valid-P12-ibm12v0?.xml",
        "ibm-valid-P13-ibm13v01.xml",
        "root",
        "v-pe00",
        # here are invalid DTDs that should pass a non-validating parser.
        "el04",
        "ibm-invalid-P45-ibm45i01.xml",
        "ibm-invalid-P49-ibm49i01.xml",
        "ibm-invalid-P50-ibm50i01.xml",
        "invalid--00[256]",
        "*not-sa14",
        "optional*",
        # while the XML spec (1.0, 5th ed.) prose tells us that the use of NameStartChar
        # shall prevent the usage of "basic combining characters" as first character of
        # a name, the formal specification of NameStartChar includes such.
        # https://www.w3.org/TR/REC-xml/#NT-NameStartChar
        "not-wf-sa-140",
        # #x0e5c is an undefined character entity, yet it's included in the formal
        # spec of name characters.
        # https://www.w3.org/TR/REC-xml/#NT-NameStartChar
        "not-wf-sa-141",
        # lxml seemingly can't handle these encodings
        "pr-xml-*",
        "utf16b",
        "weekly-*",
    },
}


class W3CTestProcess(Process):
    def __init__(self, case: W3CConformanceTest):
        self.case = case
        super().__init__()

    def run(self):
        try:
            Document(
                self.case.path,
                parser_options=ParserOptions(
                    load_referenced_resources=True,
                    preferred_parsers=self.case.parser,
                ),
            )
        # non-validating parsers shall accept tests with the types
        # "valid" and "invalid"
        except FailedDocumentLoading as e:
            if self.case.type.endswith("valid"):
                raise e.excuses[path_loader]
        except Exception:
            if self.case.type.endswith("valid"):
                raise
        else:
            assert self.case.type.endswith("valid")


def collect_w3c_conformance_tests():
    suite_path = Path(__file__).parent / "w3c_conformance_test_suite_20020606"
    cases_path: Path | None = None

    for event, element in etree.iterparse(
        suite_path / "xmlconf-20020606.xml", events=("start", "end"), load_dtd=True
    ):

        if event == "start":
            if (
                element.tag == "TESTCASES"
                and (
                    base := element.attrib.get(
                        "{http://www.w3.org/XML/1998/namespace}base"
                    )
                )
                is not None
            ):
                cases_path = suite_path / base

        else:
            if element.tag == "TESTCASES":
                element.clear()
                continue
            elif element.tag != "TEST":
                continue

            attributes = element.attrib
            sections = attributes["SECTIONS"]
            if any(s in sections.split() for s in IGNORED_SECTIONS):
                continue

            id_ = attributes["ID"]
            if any(fnmatch(id_, p) for p in IGNORED_TESTS[None]):
                continue

            for parser in plugin_manager.parsers:
                if any(fnmatch(id_, p) for p in IGNORED_TESTS[parser]):
                    continue

                yield W3CConformanceTest(
                    parser=parser,
                    path=cases_path / attributes["URI"],
                    entities=attributes["ENTITIES"],
                    id=id_,
                    sections=sections,
                    type="valid" if id_ in ACTUALLY_VALID_CASES else attributes["TYPE"],
                )


@pytest.mark.parametrize("case", collect_w3c_conformance_tests())
def test_w3c_test_suite(case):
    # invalid documents and encoding problems may crash the application or evoke side
    # effects on other tests. hence they're executed in a subprocess.
    test = W3CTestProcess(case)
    test.start()
    test.join()
    assert test.exitcode == 0

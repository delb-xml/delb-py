import pytest

from delb import Document, ParserOptions

from benchmarks.conftest import XML_FILES


def parse_file(file, parser_options):
    Document(file, parser_options)


@pytest.mark.parametrize("file", XML_FILES)
@pytest.mark.parametrize("parser", ("expat", "lxml"))
@pytest.mark.parametrize("all_contents", (True, False))
def test_parsing_files(benchmark, file, parser, all_contents):
    parser_options = ParserOptions(
        load_referenced_resources=True,
        preferred_parsers=parser,
        remove_comments=not all_contents,
        remove_processing_instructions=not all_contents,
    )
    benchmark(parse_file, file, parser_options)

from delb import Document


def reading_and_parsing_files(docs):
    for file in docs:
        Document(file)


def test_reading_and_parsing_files(benchmark, docs):
    benchmark(reading_and_parsing_files, docs)

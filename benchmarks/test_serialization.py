from delb import Document


def serialize_documents(docs):
    for doc in docs:
        str(doc)


def test_serialization(benchmark, docs):
    benchmark(serialize_documents, [Document(x) for x in docs])

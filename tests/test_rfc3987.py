from pytest import mark

from _delb.rfc3987 import is_iri_compliant


@mark.parametrize(
    "string",
    (
        # source: https://www.w3.org/International/iri-edit/BidiExamples
        #         (examples 8-9, items a & i)
        "http://ab.cd.ef/זח1/2טי/כל.html",
        "http://ab.cd.ef/خد1/2ذر/زس.html",
        "http://ab.cd.ef/זח%31/%32טי/כל.html",
        "http://ab.cd.ef/خد%31/%32ذر/زس.html",
        #
        "foo",
    ),
)
def test_invalid_iri(string):
    assert is_iri_compliant(string)


@mark.parametrize(
    "string",
    (
        # source:
        #     https://www.w3.org/International/tests/test-incubator/oldtests/sec-idn-0
        "http://点心和烤鸭.w3.mag.keio.ac.jp",
        "http://www.w3.org/International/articles/idn-and-iri/JP納豆/引き割り納豆.html",
        # source: https://www.w3.org/International/iri-edit/BidiExamples
        #         (examples 1-7, items a & i)
        "http://ab.גדהוזח.ij/kl/mn/op.html",
        "http://ab.تثجحخد.ij/kl/mn/op.html",
        "http://ab.גדה.וזח/ij/kl/mn/op.html",
        "http://ab.تثج.حخد/ij/kl/mn/op.html",
        "http://אב.גד.הו/זח/טי/כל?מן=סע;פץ=קר#שת",
        "http://اب.تث.جح/خد/ذر/زس?شص=ضط;ظع=غف#قك",
        "http://אב.גד.ef/gh/טי/כל.html",
        "http://اب.تث.ef/gh/ذر/زس.html",
        "http://ab.cd.הו/זח/ij/kl.html",
        "http://ab.cd.جح/خد/ij/kl.html",
        "http://ab.גד.הו/זח/טי/kl.html",
        "http://ab.تث.جح/خد/ذر/kl.html",
        "http://ab.גדה123וזח.ij/kl/mn/op.html",
        "http://ab.تثج123حخد.ij/kl/mn/op.html"
        # source: https://www.w3.org/2001/08/iri-test/
        "ほんとうにながいわけのわからないどめいんめいのらべるまだながくしないとたりない.ほんとうに"
        "ながいわけのわからないどめいんめいのらべるまだながくしないとたりない.ほんとうにながいわけ"
        "のわからないどめいんめいのらべるまだながくしないとたりない.w3.mag.keio.ac.jp",
        #
        "https://www.delb/",
    ),
)
def test_valid_iri(string):
    assert is_iri_compliant(string)

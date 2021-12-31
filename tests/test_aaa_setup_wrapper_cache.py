from delb import Document


# these objects will be used in test_zzz_wrapper_cache
def test_setup_long_term_references(long_term_references):
    long_term_references["a_document"] = Document("<document/>")

    root = Document("<root>a</root>").root
    root.append_child("b")
    long_term_references["appended_b"] = root.last_child

    root = Document("<root>a</root>").root
    root.append_child("b")
    root.append_child("c")
    long_term_references["appended_b_with_c"] = root.last_child

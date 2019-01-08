from xmldiff import main as xmldiff


def assert_documents_are_semantical_equal(old, new):
    changes = xmldiff.diff_files(
        str(old), str(new), diff_options={"F": 1.0, "ratio_mode": "accurate"}
    )
    assert not changes, changes

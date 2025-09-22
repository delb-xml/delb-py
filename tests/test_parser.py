import pytest

from _delb.plugins import plugin_manager
from _delb.parser import detect_encoding


@pytest.mark.parametrize(
    ("stream", "encoding"),
    (
        (b"\xff\xfe\00\x00<root/>", "utf-32-le"),
        (b"\x00\x00\xfe\xff<root/>", "utf-32-be"),
        (b"\xef\xbb\xbf<root/>", "utf-8"),
        (b"\xff\xfe<root/>", "utf-16-le"),
        (b"\xfe\xff<root/>", "utf-16-be"),
    ),
)
def test_bom_detection(stream, encoding):
    assert detect_encoding(stream) == encoding


def test_get_parser():
    with pytest.raises(ValueError, match="No matching parser"):
        assert plugin_manager.get_parser("unavailable")

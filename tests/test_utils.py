import pytest

from delb import Document


@pytest.mark.parametrize(
    "obj",
    (
        Document("<pb n='[III]'/>").root["n"],
        Document("<root>[III]</root>").root.first_child,
    ),
)
def test_value_strip(obj):
    assert obj == "[III]"
    assert obj.startswith("[")
    assert "III" in obj
    assert obj.strip("[]") == "III"
    assert obj[1:-1] == "III"

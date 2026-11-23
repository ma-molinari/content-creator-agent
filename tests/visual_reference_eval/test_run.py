import pytest
from PIL import Image

from run import resolved_color
from run_ambiguous_carousel import prepare_references


def test_resolves_v1_and_v2_colors():
    snapshot = {"palette": {"accent": "#F26930"}}
    assert resolved_color(snapshot, "#123456") == "#123456"
    assert resolved_color(snapshot, {"hex": "#FFFFFF"}) == "#FFFFFF"
    assert resolved_color(snapshot, {"token": "accent"}) == "#F26930"
    with pytest.raises(ValueError):
        resolved_color(snapshot, {"token": "accent", "hex": "#FFFFFF"})


def test_authorized_references_are_validated_and_copied_locally(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (2, 2), "red").save(source)
    destination = tmp_path / "output"
    destination.mkdir()
    paths = prepare_references(destination, [source])
    assert paths[0].read_bytes() == source.read_bytes()
    with pytest.raises(ValueError):
        prepare_references(destination, [source] * 9)
    invalid = tmp_path / "invalid.png"
    invalid.write_text("invalid")
    with pytest.raises(OSError):
        prepare_references(destination, [invalid])

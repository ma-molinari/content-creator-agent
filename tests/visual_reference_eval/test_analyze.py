import pytest

from analyze import contrast, distance


def test_cielab_distance_is_zero_for_same_color_and_symmetric():
    assert distance('#291044', '#291044') == 0
    assert distance('#291044', '#fff5e9') == pytest.approx(distance('#fff5e9', '#291044'))
    assert distance('#ff0000', '#00ff00') == pytest.approx(170.6, abs=0.2)


def test_contrast_ratio_for_black_and_white():
    assert contrast('#000000', '#ffffff') == pytest.approx(21)
    assert contrast('#ffffff', '#000000') == pytest.approx(21)
    assert contrast('#123456', '#123456') == pytest.approx(1)

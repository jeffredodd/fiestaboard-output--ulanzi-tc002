"""Rendering: core's 52 x 17 layout squeezed onto the clock's 52 x 16."""

from __future__ import annotations

import pytest
from plugins.ulanzi_tc002 import GAP_ROW, PANEL_HEIGHT, PANEL_WIDTH, squeeze

from src.led import grid_layout
from src.plugins import layout_message, rasterize

from .conftest import build, grid

WHITE_ON = 0xFF


def rows_lit(pixels: bytes, width: int) -> list[bool]:
    stride = width * 3
    return [any(pixels[y * stride : (y + 1) * stride]) for y in range(len(pixels) // stride)]


def test_the_gap_row_is_the_gap_between_the_second_and_third_text_row():
    layout = grid_layout(52, 17, "3x5")
    assert (layout.rows, layout.cols, layout.origin_y) == (3, 13, 0)
    # Text rows at 0-4, 6-10 and 12-16: the gaps are 5 and 11.
    assert GAP_ROW == layout.origin_y + 2 * 6 - 1


def test_a_frame_is_exactly_the_panel():
    pixels = build({"host": "192.0.2.10"}).render(grid(1))
    assert len(pixels) == PANEL_WIDTH * PANEL_HEIGHT * 3


def test_three_rows_of_text_keep_the_gap_under_the_first_and_lose_the_second():
    plugin = build({"host": "192.0.2.10"})
    full = rasterize(plugin.layout(grid(69)))  # 69: white tiles fill every glyph box
    assert (full.width, full.height) == (52, 17)
    assert rows_lit(full.pixels, 52) == [True] * 5 + [False] + [True] * 5 + [False] + [True] * 5

    squeezed = plugin.render(grid(69))
    assert rows_lit(squeezed, 52) == [True] * 5 + [False] + [True] * 10


def test_two_rows_of_text_keep_their_gap_and_move_to_the_middle():
    plugin = build({"host": "192.0.2.10"})
    frame = [[69] * 13, [69] * 13, [0] * 13]
    squeezed = plugin.render(frame)
    assert rows_lit(squeezed, 52) == [False] * 2 + [True] * 5 + [False] + [True] * 5 + [False] * 3

    full = rasterize(plugin.layout(frame))
    stride = 52 * 3
    assert squeezed[2 * stride : 13 * stride] == full.pixels[: 11 * stride], "every pixel of the two rows, two down"


def test_anything_in_the_third_row_keeps_three_rows():
    plugin = build({"host": "192.0.2.10"})
    one_tile = [[69] * 13, [0] * 13, [0] * 12 + [63]]
    assert rows_lit(plugin.render(one_tile), 52) == [True] * 5 + [False] * 6 + [True] * 5


def test_every_lit_pixel_but_the_gap_row_survives():
    plugin = build({"host": "192.0.2.10"})
    frame = [[(r * 13 + c) % 26 + 1 for c in range(13)] for r in range(3)]
    full = rasterize(plugin.layout(frame))
    stride = 52 * 3
    kept = b"".join(full.pixels[y * stride : (y + 1) * stride] for y in range(17) if y != GAP_ROW)
    assert plugin.render(frame) == kept


@pytest.mark.parametrize(("width", "height"), [(52, 16), (40, 10), (60, 20)])
def test_other_sizes_are_cut_or_padded_to_the_panel(width, height):
    pixels = bytes([WHITE_ON]) * (width * height * 3)
    out = squeeze(pixels, width, height)
    assert len(out) == PANEL_WIDTH * PANEL_HEIGHT * 3


def test_rich_cells_and_codes_draw_the_same_page():
    from src.plugins import cells_from_codes

    plugin = build({"host": "192.0.2.10"})
    codes = [[8, 9, 0, 63] + [0] * 9, [0] * 13, [0] * 13]
    assert plugin.render(codes) == plugin.render(cells_from_codes(codes))


def test_layers_reach_the_renderer_when_the_frame_carries_them(monkeypatch):
    import plugins.ulanzi_tc002 as module

    seen = {}

    def fake_layout(tokens, spec, options, layers=()):
        seen["layers"] = layers
        return layout_message(tokens, spec, options)

    monkeypatch.setattr(module, "layout_message", fake_layout)

    class Frame(list):
        layers = ("canvas",)

    plugin = build({"host": "192.0.2.10"})
    plugin.render(Frame(grid(1)))
    assert seen["layers"] == ("canvas",)

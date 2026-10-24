"""Shared fixtures: a mock AWTRIX NG clock on loopback and plugins pointed at it.

Every test talks to :class:`~tests.mock_awtrix.MockAwtrix` on 127.0.0.1; the
network fence (pytest-socket, ``--allow-hosts=127.0.0.1``) refuses anything
else, so no test can reach a real clock.

``make_plugin`` builds an :class:`AwtrixNG` the way core does (the manifest's
``output`` block bound, ``open()`` called) and shortens the pacing constants
so tests run fast. Tests that are *about* pacing set them back explicitly.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from plugins.awtrix_ng import AwtrixNG

from src.plugins.manifest import load_manifest

from .mock_awtrix import MockAwtrix

PLUGIN_DIR = Path(__file__).resolve().parent.parent
MANIFEST, _ERRORS = load_manifest(PLUGIN_DIR / "manifest.json")

#: The board's grid: 3 rows x 13 columns of the 3x5 face on the 52 x 17 model.
ROWS, COLS = 3, 13


def grid(code: int) -> list[list[int]]:
    return [[code] * COLS for _ in range(ROWS)]


def render(frame) -> bytes:
    """A frame (0-71 codes or rich cells) as the 52 x 16 RGB888 a bound plugin sends."""
    return build({"host": "192.0.2.10"}).render(frame)


@pytest.fixture
def clock():
    device = MockAwtrix().start()
    yield device
    device.stop()


def build(config: dict, *, fast: bool = True) -> AwtrixNG:
    plugin = AwtrixNG("board-test", config)
    if MANIFEST is not None and MANIFEST.output is not None:
        plugin.bind_manifest(MANIFEST.output)
    if fast:
        plugin.STREAM_STEP_S = 0.0
        plugin.CONNECT_TIMEOUT_S = 0.5
        plugin.READ_TIMEOUT_S = 0.5
    plugin.open()
    return plugin


@pytest.fixture
def make_plugin(clock):
    built: list[AwtrixNG] = []

    def factory(fast: bool = True, **config) -> AwtrixNG:
        config.setdefault("host", clock.host)
        plugin = build(config, fast=fast)
        built.append(plugin)
        return plugin

    yield factory
    for plugin in built:
        plugin.close()

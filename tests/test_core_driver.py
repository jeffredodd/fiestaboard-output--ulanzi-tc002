"""Core's driver adapter in front of the plugin, against the mock clock.

The plugin never spaces writes itself; core's floor (``min_interval_ms``
1000, keyed by ``device_key()``) does. This drives the plugin the way a board
does and checks the clock sees exactly what core lets through.
"""

from __future__ import annotations

from src.outputs.plugin_driver import OutputPluginDriver

from .conftest import grid


def test_core_keeps_the_one_second_floor_between_writes(clock, make_plugin):
    now = [10_000.0]
    driver = OutputPluginDriver(make_plugin(), clock=lambda: now[0])

    first = driver.send_characters(grid(1), with_outcome=True)
    assert (first.success, first.was_sent) == (True, True)

    now[0] += 0.5
    second = driver.send_characters(grid(2), with_outcome=True)
    assert second.throttled and not second.was_sent
    assert len(clock.pushes()) == 1


def test_a_dead_clock_is_a_failed_write_core_can_report(clock, make_plugin):
    clock.mode = "http_500"
    driver = OutputPluginDriver(make_plugin())
    result = driver.send_characters(grid(1), with_outcome=True)
    assert (result.success, result.was_sent) == (False, False)
    assert driver.last_write_error


def test_core_streams_a_page_change_through_the_models_flip(clock, make_plugin):
    now = [20_000.0]
    driver = OutputPluginDriver(make_plugin(), clock=lambda: now[0])
    assert driver.takes_transitions
    driver.send_characters(grid(1))
    now[0] += 2.0
    clock.clear()

    result = driver.render(grid(2), with_outcome=True)

    assert (result.success, result.was_sent) == (True, True)
    assert len(clock.pushes()) > 1

"""tools/try_device.py against the mock clock: it runs its two steps and reports them."""

from __future__ import annotations

import importlib.util
import io
import json

from .conftest import PLUGIN_DIR
from .mock_awtrix import ACTIVE, PUSHED


def load_tool():
    spec = importlib.util.spec_from_file_location("try_device", PLUGIN_DIR / "tools" / "try_device.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_it_shows_a_still_then_one_change_and_reports_every_request(clock, tmp_path):
    tool = load_tool()
    out = io.StringIO()

    report = tool.run({"host": clock.host, "app_name": "Try"}, pause_s=0, transition="slide", out=out)

    assert [s["result"]["success"] for s in report["steps"]] == [True, True, True]
    paths = [(c["method"], c["path"]) for c in report["calls"]]
    assert paths[0] == ("GET", "/api/v1/device")
    assert ("PUT", PUSHED + "Try") in paths and ("PUT", ACTIVE) in paths
    assert all("bytes" in c for c in report["calls"] if c["path"].startswith(PUSHED))
    assert "AWTRIX NG at" in out.getvalue()

    target = tmp_path / "report.json"
    assert tool.main(["--host", clock.host, "--pause", "0", "--json", str(target)]) == 0
    assert json.loads(target.read_text())["app"] == "FiestaBoard"


def test_it_fails_when_the_clock_does(clock):
    clock.mode = "http_500"
    tool = load_tool()
    assert tool.main(["--host", clock.host, "--pause", "0", "--user", "admin", "--password", "x"]) == 1

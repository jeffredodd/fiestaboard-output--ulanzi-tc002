"""Find my clock: which networks are searched and what answers like AWTRIX NG."""

from __future__ import annotations

import ipaddress

import plugins.awtrix_ng as module
import pytest
from plugins.awtrix_ng import AwtrixNG, candidate_subnets, is_awtrix_reply, sweep

from src.plugins import OutputHttp

from .mock_awtrix import MockAwtrix


def nets(*names: str) -> list[ipaddress.IPv4Network]:
    return [ipaddress.IPv4Network(n) for n in names]


def test_an_awtrix_reply_has_a_board_type_and_a_uid():
    assert is_awtrix_reply({"boardType": "tc002", "uid": "x"})
    assert is_awtrix_reply({"boardType": "awtrixng", "uid": "x"})
    assert not is_awtrix_reply({"boardType": "tc002"})
    assert not is_awtrix_reply({"error_code": 0, "Brightness": 50})
    assert not is_awtrix_reply([1])


def test_networks_in_order_without_duplicates():
    assert candidate_subnets(subnet="192.168.1.0/24", hint_host="192.168.1.20", local_ip="10.0.0.5") == nets(
        "192.168.1.0/24", "10.0.0.0/24"
    )
    assert candidate_subnets(hint_host="192.168.2.7", local_ip="192.168.2.9") == nets("192.168.2.0/24")


def test_a_docker_bridge_is_skipped_once_a_network_is_known():
    assert candidate_subnets(hint_host="192.168.1.20", local_ip="172.17.0.2") == nets("192.168.1.0/24")
    assert candidate_subnets(local_ip="172.17.0.2") == nets("172.17.0.0/24")


@pytest.mark.parametrize("subnet", ["8.8.8.0/24", "10.0.0.0/16", "not a network"])
def test_public_huge_or_malformed_networks_are_refused(subnet):
    with pytest.raises(ValueError):
        candidate_subnets(subnet=subnet)


def test_public_loopback_and_unresolvable_hints_are_ignored():
    assert candidate_subnets(hint_host="8.8.8.8", local_ip="127.0.0.1") == []
    assert candidate_subnets(hint_host="no-such-host.invalid") == []
    assert candidate_subnets(hint_host="::1") == []


def test_a_sweep_finds_the_clock_and_labels_it(clock):
    other = MockAwtrix().start()
    other.mode = "other_json"
    try:
        ip, port = clock.server.server_address[:2]
        found = sweep(OutputHttp(), [("127.0.0.1", other.server.server_address[1]), (ip, port)], per_host_s=0.5)
    finally:
        other.stop()
    assert len(found) == 1
    assert found[0]["host"] == f"{ip}:{port}"
    assert found[0]["label"] == f"awtrixng-ab34cd at {ip} (TC002)"


def test_find_my_clock_reports_what_it_found(clock, make_plugin, monkeypatch):
    ip, port = clock.server.server_address[:2]
    monkeypatch.setattr(module, "local_ipv4", lambda: None)
    monkeypatch.setattr(module, "candidate_subnets", lambda **kw: nets("192.168.1.0/30"))
    monkeypatch.setattr(module, "_targets", lambda networks, p: [(ip, port)])
    plugin = make_plugin()

    outcome = plugin.run_action("find_awtrix", {})

    assert outcome.status == "ok"
    assert [d["host"] for d in outcome.devices] == [f"{ip}:{port}"]


def test_find_my_clock_guides_when_nothing_answers(clock, make_plugin, monkeypatch):
    monkeypatch.setattr(module, "local_ipv4", lambda: None)
    monkeypatch.setattr(module, "_targets", lambda networks, p: [])
    plugin = make_plugin()

    nothing = plugin.run_action("find_awtrix", {"subnet": "192.168.1.0/24"})
    assert nothing.status == "warning" and nothing.devices == ()
    assert any("password" in g for g in nothing.guidance)

    assert plugin.run_action("find_awtrix", {}).status == "warning"  # no network known
    assert plugin.run_action("find_awtrix", {"subnet": "8.8.8.0/24"}).status == "error"


def test_find_my_clock_mentions_the_host_fence(clock, make_plugin, monkeypatch):
    monkeypatch.setenv("FIESTABOARD_OUTPUTS_ALLOW_HOSTS", "192.0.2.99")
    monkeypatch.setattr(module, "local_ipv4", lambda: None)
    monkeypatch.setattr(module, "_targets", lambda networks, p: [])
    outcome = make_plugin().run_action("find_awtrix", {"subnet": "192.168.1.0/24"})
    assert "FIESTABOARD_OUTPUTS_ALLOW_HOSTS" in outcome.guidance[0]


def test_core_discover_hook_sweeps_the_hint(clock, monkeypatch):
    ip, port = clock.server.server_address[:2]
    seen = {}

    def fake_targets(networks, p):
        seen["networks"] = networks
        return [(ip, port)]

    monkeypatch.setattr(module, "local_ipv4", lambda: "10.1.2.3")
    monkeypatch.setattr(module, "_targets", fake_targets)
    found = AwtrixNG.discover(2.0, hint="192.168.5.5")
    assert seen["networks"] == nets("192.168.5.0/24", "10.1.2.0/24")
    assert [d["ip"] for d in found] == [ip]

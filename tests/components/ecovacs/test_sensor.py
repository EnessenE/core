"""Tests for Ecovacs sensors."""

from deebot_client.event_bus import EventBus
from deebot_client.events import (
    BatteryEvent,
    ErrorEvent,
    LifeSpan,
    LifeSpanEvent,
    NetworkInfoEvent,
    StatsEvent,
    TotalStatsEvent,
)
import pytest
from syrupy import SnapshotAssertion

from homeassistant.components.ecovacs.controller import EcovacsController
from homeassistant.const import STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .util import block_till_done

pytestmark = [pytest.mark.usefixtures("init_integration")]


async def notify_events(hass: HomeAssistant, event_bus: EventBus):
    """Notify events."""
    event_bus.notify(StatsEvent(10, 5 * 60, "spotArea"))
    event_bus.notify(TotalStatsEvent(60, 40 * 60, 123))
    event_bus.notify(BatteryEvent(100))
    event_bus.notify(BatteryEvent(100))
    event_bus.notify(
        NetworkInfoEvent("192.168.0.10", "Testnetwork", -62, "AA:BB:CC:DD:EE:FF")
    )
    event_bus.notify(LifeSpanEvent(LifeSpan.BRUSH, 80, 60 * 60))
    event_bus.notify(LifeSpanEvent(LifeSpan.FILTER, 56, 40 * 60))
    event_bus.notify(LifeSpanEvent(LifeSpan.SIDE_BRUSH, 40, 20 * 60))
    event_bus.notify(ErrorEvent(0, "NoError: Robot is operational"))
    await block_till_done(hass, event_bus)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("device_fixture", "entity_ids"),
    [
        (
            "yna5x1",
            [
                "sensor.ozmo_950_stats_area",
                "sensor.ozmo_950_stats_time",
                "sensor.ozmo_950_stats_type",
                "sensor.ozmo_950_stats_total_area",
                "sensor.ozmo_950_stats_total_time",
                "sensor.ozmo_950_stats_total_cleanings",
                "sensor.ozmo_950_battery",
                "sensor.ozmo_950_ip",
                "sensor.ozmo_950_wifi_rssi",
                "sensor.ozmo_950_wifi_ssid",
                "sensor.ozmo_950_brush",
                "sensor.ozmo_950_filter",
                "sensor.ozmo_950_side_brush",
                "sensor.ozmo_950_last_error",
            ],
        ),
    ],
)
async def test_sensors(
    hass: HomeAssistant,
    controller: EcovacsController,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    entity_ids: list[str],
) -> None:
    """Test that sensor entity snapshots match."""
    assert entity_ids == hass.states.async_entity_ids(Platform.SENSOR)
    for entity_id in entity_ids:
        assert (state := hass.states.get(entity_id)), f"State of {entity_id} is missing"
        assert state.state == STATE_UNKNOWN

    await notify_events(hass, controller.devices[0].events)
    for entity_id in entity_ids:
        assert (state := hass.states.get(entity_id)), f"State of {entity_id} is missing"
        assert snapshot(name=f"{entity_id}:state") == state

        assert (entity_entry := entity_registry.async_get(state.entity_id))
        assert snapshot(name=f"{entity_id}:entity-registry") == entity_entry

        assert entity_entry.device_id


@pytest.mark.parametrize(
    ("device_fixture", "entity_ids"),
    [
        (
            "yna5x1",
            [
                "sensor.ozmo_950_ip",
                "sensor.ozmo_950_wifi_rssi",
                "sensor.ozmo_950_wifi_ssid",
                "sensor.ozmo_950_last_error",
            ],
        ),
    ],
)
async def test_disabled_by_default_sensors(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, entity_ids: list[str]
) -> None:
    """Test the disabled by default sensors."""
    for entity_id in entity_ids:
        assert not hass.states.get(entity_id)

        assert (entry := entity_registry.async_get(entity_id))
        assert entry.disabled
        assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION

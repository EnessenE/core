"""Tests for the TechnoVE sensor platform."""
from datetime import timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy import SnapshotAssertion
from technove import Status, TechnoVEError

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "mock_technove")
async def test_sensors(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the creation and values of the TechnoVE sensors."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entity_registry = er.async_get(hass)
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )

    assert entity_entries
    for entity_entry in entity_entries:
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert hass.states.get(entity_entry.entity_id) == snapshot(
            name=f"{entity_entry.entity_id}-state"
        )


@pytest.mark.parametrize(
    "entity_id",
    (
        "sensor.technove_station_signal_strength",
        "sensor.technove_station_wi_fi_network_name",
    ),
)
@pytest.mark.usefixtures("init_integration")
async def test_disabled_by_default_sensors(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, entity_id: str
) -> None:
    """Test the disabled by default TechnoVE sensors."""
    assert hass.states.get(entity_id) is None

    assert (entry := entity_registry.async_get(entity_id))
    assert entry.disabled
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_no_wifi_support(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_technove: MagicMock,
) -> None:
    """Test missing Wi-Fi information from TechnoVE device."""
    # Remove Wi-Fi info
    device = mock_technove.update.return_value
    device.info.network_ssid = None

    # Setup
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert (state := hass.states.get("sensor.technove_station_wi_fi_network_name"))
    assert state.state == STATE_UNKNOWN


@pytest.mark.usefixtures("init_integration")
async def test_sensor_update_failure(
    hass: HomeAssistant,
    mock_technove: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test coordinator update failure."""
    entity_id = "sensor.technove_station_status"

    assert hass.states.get(entity_id).state == Status.PLUGGED_CHARGING.value

    freezer.tick(timedelta(minutes=5, seconds=1))
    async_fire_time_changed(hass)
    mock_technove.update.side_effect = TechnoVEError("Test error")
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

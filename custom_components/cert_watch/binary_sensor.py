from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_CA_VALID, ATTR_SELF_SIGNED, DOMAIN
from .coordinator import CertWatchCoordinator

BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key=ATTR_CA_VALID,
        name="Certificate CA valid",
        icon="mdi:check-decagram",
    ),
    BinarySensorEntityDescription(
        key=ATTR_SELF_SIGNED,
        name="Certificate self-signed",
        icon="mdi:shield-alert",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CertWatchCoordinator = hass.data[DOMAIN][entry.entry_id]
    base = f"{entry.data['host']}:{entry.data['port']}"
    async_add_entities(
        [CertWatchBinarySensor(coordinator, desc, base, entry.entry_id) for desc in BINARY_SENSORS]
    )


class CertWatchBinarySensor(CoordinatorEntity[CertWatchCoordinator], BinarySensorEntity):
    def __init__(
        self,
        coordinator: CertWatchCoordinator,
        description: BinarySensorEntityDescription,
        base: str,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = f"{base} {description.name}"
        self._attr_unique_id = f"{base}:{description.key}"

    @property
    def is_on(self) -> bool | None:
        val = self.coordinator.data.get(self.entity_description.key)
        return None if val is None else bool(val)

    @property
    def device_info(self) -> DeviceInfo:
        host = self.coordinator.host
        port = self.coordinator.port
        return DeviceInfo(
            identifiers={(DOMAIN, f"{host}:{port}")},
            name=f"{host}:{port}",
            manufacturer="Cert Watch",
            model="TLS Certificate Monitor",
            configuration_url=f"https://{host}:{port}" if port == 443 else None,
        )

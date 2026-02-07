from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_DAYS_REMAINING, ATTR_NOT_AFTER, ATTR_STATUS, DOMAIN
from .coordinator import CertWatchCoordinator

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=ATTR_DAYS_REMAINING,
        name="Certificate days remaining",
        icon="mdi:calendar-clock",
        native_unit_of_measurement="days",
    ),
    SensorEntityDescription(
        key=ATTR_NOT_AFTER,
        name="Certificate not after",
        icon="mdi:certificate",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=ATTR_STATUS,
        name="Certificate status",
        icon="mdi:shield-check",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CertWatchCoordinator = hass.data[DOMAIN][entry.entry_id]
    base = f"{entry.data['host']}:{entry.data['port']}"
    async_add_entities(
        [CertWatchSensor(coordinator, desc, base, entry.entry_id) for desc in SENSORS]
    )


class CertWatchSensor(CoordinatorEntity[CertWatchCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: CertWatchCoordinator,
        description: SensorEntityDescription,
        base: str,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = f"{base} {description.name}"
        self._attr_unique_id = f"{base}:{description.key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self.entity_description.key)

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

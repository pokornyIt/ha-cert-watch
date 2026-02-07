from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import socket
import ssl
import tempfile
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ATTR_CA_VALID,
    ATTR_DAYS_REMAINING,
    ATTR_NOT_AFTER,
    ATTR_SELF_SIGNED,
    ATTR_STATUS,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_SNI,
    DEFAULT_TIMEOUT_SECONDS,
    STATUS_EXPIRED,
    STATUS_EXPIRING,
    STATUS_OK,
)


@dataclass(frozen=True)
class CertResult:
    not_after: datetime
    days_remaining: int
    self_signed: bool
    ca_valid: bool
    status: str


def _parse_not_after(value: str) -> datetime:
    # ssl.getpeercert() returns e.g. "Jun  1 12:00:00 2026 GMT"
    dt = datetime.strptime(value, "%b %d %H:%M:%S %Y %Z")
    return dt.replace(tzinfo=UTC)


def _issuer_subject_str(cert_dict: dict[str, Any], key: str) -> str:
    # cert_dict["issuer"] is tuple-of-tuples-of-tuples (OpenSSL-ish)
    parts = []
    for rdn in cert_dict.get(key, ()):
        for item in rdn:
            if isinstance(item, tuple) and len(item) == 2:
                parts.append(f"{item[0]}={item[1]}")
    return ",".join(parts)


def _decode_der_cert(der_bytes: bytes) -> dict[str, Any]:
    """Decode DER cert to the same dict structure as getpeercert()."""
    pem = ssl.DER_cert_to_PEM_cert(der_bytes)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=True) as f:
        f.write(pem)
        f.flush()
        # Internal helper, but widely used for exactly this use-case
        return ssl._ssl._test_decode_cert(f.name)  # type: ignore[attr-defined]


def _fetch_cert_result(
    host: str, port: int, sni: str | None, timeout_s: int = DEFAULT_TIMEOUT_SECONDS
) -> CertResult:
    server_name = sni or host

    # 1) Try verified handshake first (best case)
    cert: dict[str, Any] | None = None
    try:
        validation_context = ssl.create_default_context()
        validation_context.check_hostname = False  # we only care about chain validity
        validation_context.check_hostname = (
            False  # We validate chain only; host may be IP or mismatched
        )
        with (
            socket.create_connection((host, port), timeout=timeout_s) as validation_socket,
            validation_context.wrap_socket(
                validation_socket, server_hostname=server_name
            ) as server_sock,
        ):
            cert = server_sock.getpeercert()
        ca_valid = True
    except ssl.SSLError:
        ca_valid = False
    except OSError:
        ca_valid = False

    # 2) If we didn't get a parsed cert, fetch DER without verification and decode
    if not cert or "notAfter" not in cert:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with (
            socket.create_connection((host, port), timeout=timeout_s) as sock,
            ctx.wrap_socket(sock, server_hostname=server_name) as secure_socket,
        ):
            der = secure_socket.getpeercert(binary_form=True)
        if not der:
            raise RuntimeError("No certificate received (empty peer cert)")
        cert = _decode_der_cert(der)

    not_after = _parse_not_after(cert["notAfter"])
    now = datetime.now(tz=UTC)
    seconds_left = int((not_after - now).total_seconds())
    days_remaining = seconds_left // 86400

    issuer = _issuer_subject_str(cert, "issuer")
    subject = _issuer_subject_str(cert, "subject")
    self_signed = bool(issuer and subject and issuer == subject)

    if seconds_left < 0:
        status = STATUS_EXPIRED
    elif days_remaining < 14:
        status = STATUS_EXPIRING
    else:
        status = STATUS_OK

    return CertResult(
        not_after=not_after,
        days_remaining=days_remaining,
        self_signed=self_signed,
        ca_valid=ca_valid,
        status=status,
    )


class CertWatchCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.port = int(entry.data[CONF_PORT])
        self.sni = (entry.data.get(CONF_SNI) or "").strip() or None
        hours = int(entry.data.get(CONF_SCAN_INTERVAL_HOURS, 12))

        super().__init__(
            hass=hass,
            logger=__import__("logging").getLogger(__name__),
            name=f"cert_watch_{self.host}_{self.port}",
            update_interval=__import__("datetime").timedelta(hours=hours),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            result: CertResult = await self.hass.async_add_executor_job(
                _fetch_cert_result, self.host, self.port, self.sni
            )
            return {
                ATTR_NOT_AFTER: result.not_after,
                ATTR_DAYS_REMAINING: result.days_remaining,
                ATTR_SELF_SIGNED: result.self_signed,
                ATTR_CA_VALID: result.ca_valid,
                ATTR_STATUS: result.status,
            }
        except Exception as exc:
            raise UpdateFailed(
                f"Failed to fetch TLS certificate for {self.host}:{self.port}: {exc}"
            ) from exc

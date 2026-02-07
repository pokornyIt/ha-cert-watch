# Cert Watch (Home Assistant)

Home Assistant custom integration to monitor TLS certificates for `host:port` targets.

## Features
- Days remaining + exact expiration (`notAfter`)
- `self-signed` heuristic (issuer == subject)
- `CA valid` check using system trust store

## Install (HACS)
1. Add this repository as a custom repository in HACS (Integration).
2. Install **Cert Watch**.
3. Restart Home Assistant.
4. Add integration: **Settings → Devices & services → Add integration → Cert Watch**.

## Configuration
Add one entry per target (host, port, optional SNI).
Default scan interval: 12 hours.

## Entities
Per target:
- Sensor: days remaining
- Sensor: not after (timestamp)
- Sensor: status (ok/expiring/expired)
- Binary sensor: CA valid
- Binary sensor: self-signed

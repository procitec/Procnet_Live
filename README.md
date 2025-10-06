# Procnet Live – Windows-first Live Process↔TCP/UDP Topology

Procnet Live renders an **interactive, live-updating map** of processes and their TCP/UDP connections in your browser. It aims for *Windows-first* performance using the WinAPI, while providing working fallbacks for Linux and macOS.

## What it does
- **Windows fast collector**: Uses `GetExtendedTcpTable` via `ctypes` (IPv4/IPv6).
- **Linux/macOS fallback**: Linux via `ss -tanpi`; macOS/others via `psutil`.
- **Live server**: Flask exposes `/` (UI) and `/api/graph` (JSON). The frontend (vis-network) updates the graph by adding/updating/removing nodes/edges without flicker and keeps a stable layout.
- **Direction & pairing**: Heuristics determine **client→server** using service-port classification; listener resolution for local peers; curved multi-edge layout.
- **UDP optional**: UDP edges are color-differentiated and tooltips include the protocol (TCP/UDP).
- **Node typing**: Rules (YAML/JSON) assign process types and labels (e.g., `database`, `service`, `qt_desktop`).
- **Icons**: PNG per type from `--icons-dir`. Smart fallback: type PNG → `service.png` → font icon.

## Requirements & install
- Python **3.9+** recommended.
- Windows 10/11 (admin may be required to see all PIDs).
- Linux with `ss` (iproute2). macOS via `psutil` fallback.

Create a venv and install:
```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt`:
```
Flask>=3.0.0
psutil>=5.9.0
PyYAML>=6.0.0
orjson>=3.9.0
```

> `orjson` is optional; the app falls back to the stdlib `json` if not present.

## Run
```bash
python -m procnet_live.main --port 8765 --interval 1.0 --rules node_types.yaml --udp --svc-ports 80,443,5432 --icons-dir ./icons
# open http://localhost:8765
```

## CLI options
| Option | Type | Default | Description |
|---|---:|---:|---|
| `--port` | int | `8765` | HTTP port for Flask. |
| `--interval` | float (s) | `1.0` | Collector sampling interval. |
| `--rules` | str (path) | `None` | YAML/JSON rule file. Relative paths are resolved robustly. |
| `--p2p-only` | flag | `False` | Render only PID↔PID edges. Suppresses external endpoints and listener edges. |
| `--udp` | flag | `False` | Include UDP connections (with raddr) and color-differentiate edges. Tooltip shows protocol. |
| `--svc-ports` | CSV of int | `''` | Additional service ports for direction heuristics (e.g., `3000,5000`). |
| `--icons-dir` | str (path) | `None` | Directory with PNG icons. See **Icons** below. |

## Rules (node_types.yaml)
Assign process **types** and optional **labels**.

Fields:
- `match_pid` *(int, optional)* – exact PID.
- `match_name` *(str, optional)* – exact name or regex (`/pattern/` or `/pattern/i`).
- `match_cmd` *(str, optional)* – substring or regex like above.
- `type` *(str, required)* – `app`, `service`, `database`, `message_broker`, `cache`, `load_balancer`, `external`, `qt_desktop`, ...
- `label` *(str, optional)* – custom display label.

Examples:
```yaml
- match_pid: 1234
  type: database
  label: "Local Postgres"

- match_name: "redis-server.exe"
  type: cache
  label: "Redis"

- match_name: "/chrome/i"
  type: app
  label: "Chrome"

- match_cmd: "--listen 0.0.0.0:5432"
  type: database
  label: "DB (Public)"

- match_cmd: "/--port\\s+(3000|5173)/i"
  type: service
  label: "Dev Server"

- match_name: "/qt|qtwebengine/i"
  type: qt_desktop
  label: "Qt App"
```

> First matching rule wins. If nothing matches: `type=app`, label = process name.

## Icons
Put PNGs in `--icons-dir` with **exact** names:
```
app.png
service.png
database.png
mq.png
cache.png
lb.png
external.png
qt_desktop.png
```
Server-side fallback: type PNG → `service.png` → font icon.

## Licenses
- **Project code:** MIT (see `LICENSE` if present).
- **Dependencies:** Flask (BSD-3-Clause), psutil (BSD), PyYAML (MIT), orjson (Apache-2.0).
- **Frontend:** vis-network (MIT) via `standalone/umd` CDN bundle.

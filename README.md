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
.venv\Scripts\activate
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

- match_cmd: "/--port\s+(3000|5173)/i"
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

## Portable / Offline Setup (`scripts/prepare_portable.py`)

### Why?
By default the UI loads **vis-network** from a CDN. For **offline/air‑gapped** environments or reproducible builds, you can vendor the JS locally and serve it with strong caching. This removes external dependencies, speeds up load times, and makes the app **portable**.

### What the script does
`scripts/prepare_portable.py` automates the following:
1. (Optionally) runs `pip install -r requirements.txt` (omit with `--skip-pip`).
2. Downloads the **vis-network UMD bundle** as a **versioned** filename:
   ```
   procnet_live/web/vendor/vis-network-<VER>.standalone.min.js
   ```
3. Downloads the **license** (MIT or Apache-2.0) from the official repo/tarball.
4. Writes a **manifest** with version and checksum:
   ```json
   {
     "vis_network_version": "9.1.6",
     "js_file": "vis-network-9.1.6.standalone.min.js",
     "sha256_js": "…"
   }
   ```

> The versioned filename enables **immutable** caching; changing the version yields a new filename (natural cache-busting).

### One-time run / update
```bash
# include requirements installation
python scripts/prepare_portable.py --version 9.1.6

# skip pip if your env is already set up
python scripts/prepare_portable.py --skip-pip --version 9.1.6
```

Expected output:
```
procnet_live/web/vendor/
 ├─ vis-network-9.1.6.standalone.min.js
 ├─ LICENSE-MIT.vis-network-9.1.6.txt     # or LICENSE-APACHE-2.0...
 └─ manifest.json
```

### How the UI decides which version to load
- On page load, the HTML (in `ui.py`) fetches **/vendor/manifest.json** (**no‑cache**).
- It reads `vis_network_version` and `js_file` from the manifest.
- It tries to load **local** `"/vendor/<js_file>"` first.
- If that fails, it falls back to the **CDN URL with the **same** version**:
  ```
  https://unpkg.com/vis-network@<VER>/standalone/umd/vis-network.min.js
  ```

This makes the version **centrally controlled** by re-running the script.

### Caching strategy
- Vendor JS (`/vendor/<file>.js`): served with
  ```
  Cache-Control: public, max-age=31536000, immutable
  ```
- Manifest (`/vendor/manifest.json`): served with
  ```
  Cache-Control: no-store, no-cache, must-revalidate, max-age=0
  ```
So browsers cache the heavy JS aggressively, while manifest changes take effect immediately.

### Debug / Logging
- **Browser console** prints what’s used:
  - `using LOCAL: /vendor/vis-network-9.1.6.standalone.min.js`
  - or: `local missing, using CDN: https://unpkg.com/...`
- **Flask logs** (server) report:
  - which vendor file was served
  - whether the manifest was found

### Troubleshooting
- **`vis is not defined`**: Ensure your vis initialization lives inside `window.startApp()`. The loader calls `startApp()` only after the library (local or CDN) has finished loading.
- **Manifest missing**: The UI uses defaults and may hit the CDN. Run `scripts/prepare_portable.py` to create `manifest.json`.
- **Upgrading vis-network**: Re-run the script with `--version X.Y.Z`. The manifest will point to the new file; thanks to the versioned filename, browsers fetch a fresh copy automatically.

## Licenses
- **Project code:** MIT (see `LICENSE` if present).
- **Dependencies:** Flask (BSD-3-Clause), psutil (BSD), PyYAML (MIT), orjson (Apache-2.0).
- **Frontend:** vis-network (MIT) via local vendor file or CDN (`standalone/umd`).

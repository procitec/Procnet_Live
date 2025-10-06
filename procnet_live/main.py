from __future__ import annotations
import argparse, threading
from .config import init_cfg_from_args
from .topology import Snapshot
from .web import create_app
from .rules import load_rules
from .collectors import collector_loop

def parse_args():
    ap = argparse.ArgumentParser(description='Windows-first live process TCP/UDP visualizer')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--interval', type=float, default=1.0)
    ap.add_argument('--rules', type=str, default=None)
    ap.add_argument('--p2p-only', action='store_true', help='only draw PID↔PID edges; no externals/listeners')
    ap.add_argument('--udp', action='store_true', help='include UDP connections where raddr is set')
    ap.add_argument('--svc-ports', type=str, default='', help='comma-separated service ports to prioritize (e.g. 3000,5000,7000)')
    ap.add_argument('--icons-dir', type=str, default=None, help='directory with PNGs named per ICON_FILENAMES mapping')
    return ap.parse_args()

def main():
    args = parse_args()
    cfg = init_cfg_from_args(args)

    snap = Snapshot()
    snap.rules = load_rules(args.rules)

    t = threading.Thread(target=collector_loop, args=(cfg, snap, args.interval), daemon=True)
    t.start()

    app = create_app(cfg, snap)
    print(f"[*] Serving on http://localhost:{args.port}")
    app.run(host='0.0.0.0', port=args.port, debug=False, use_reloader=False)

if __name__ == '__main__':
    main()

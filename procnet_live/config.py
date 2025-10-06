from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set
from .utils.path import to_abs_path

@dataclass
class CFG:
    p2p_only: bool = False
    udp_enabled: bool = False
    svc_ports: Set[int] = field(default_factory=set)
    icons_dir: Optional[Path] = None
    icons_map: Dict[str, str] = field(default_factory=dict)

PORT_CLASS = {
    80: ("web", "#3489eb"), 443: ("web", "#3489eb"), 8080: ("web", "#3489eb"),
    5432: ("db", "#29a36a"), 3306: ("db", "#29a36a"), 1433: ("db", "#29a36a"), 27017: ("db", "#29a36a"),
    6379: ("cache", "#b68900"),
    5672: ("mq", "#e84a5f"), 9092: ("mq", "#e84a5f"),
    22: ("infra", "#888"), 25: ("infra", "#888"), 53: ("infra", "#888"), 123: ("infra", "#888"),
}
DEFAULT_EDGE_COLOR = "#7f7f7f"
UDP_EDGE_COLOR = "#00c2ff"
DEFAULT_SERVICE_PORTS = set(PORT_CLASS.keys())

STATE_STYLE = {
    "ESTABLISHED": {"dashes": False},
    "SYN_SENT": {"dashes": [2,6]},
    "SYN_RECEIVED": {"dashes": [6,6]},
    "TIME_WAIT": {"dashes": [10,6]},
    "CLOSE_WAIT": {"dashes": [4,6]},
}

NODE_TYPE_STYLE = {
    "app":        {"color": "#9aa0a6", "icon": ""},
    "service":    {"color": "#6aa84f", "icon": ""},
    "database":   {"color": "#3c78d8", "icon": ""},
    "message_broker": {"color": "#e06666", "icon": ""},
    "cache":      {"color": "#b68900", "icon": ""},
    "load_balancer": {"color": "#8e7cc3", "icon": ""},
    "external":   {"color": "#ff9900", "icon": ""},
    "qt_desktop": {"color": "#00b894", "icon": ""},
}

ICON_FILENAMES = {
    "app": "app.png",
    "service": "service.png",
    "database": "database.png",
    "message_broker": "mq.png",
    "cache": "cache.png",
    "load_balancer": "lb.png",
    "external": "external.png",
    "qt_desktop": "qt_desktop.png",
}

def init_cfg_from_args(args) -> CFG:
    cfg = CFG()
    cfg.p2p_only = bool(args.p2p_only)
    cfg.udp_enabled = bool(args.udp)
    if getattr(args, "svc_ports", ""):
        try:
            cfg.svc_ports = {int(x.strip()) for x in args.svc_ports.split(",") if x.strip()}
        except Exception:
            cfg.svc_ports = set()
    if getattr(args, "icons_dir", None):
        p = to_abs_path(args.icons_dir)
        if p.exists() and p.is_dir():
            cfg.icons_dir = p
            from .config import ICON_FILENAMES
            for k, fname in ICON_FILENAMES.items():
                fpath = p / fname
                if fpath.exists():
                    cfg.icons_map[k] = fname
            print(f"[*] icons-dir: {p}")
    else:
        print(f"[warn] --icons-dir '{args.icons_dir}' not found or not a directory")
    return cfg

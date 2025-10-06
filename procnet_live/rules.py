from __future__ import annotations
from pathlib import Path
import json
from typing import List, Optional
from .utils.path import to_abs_path
try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from .models import Proc  # noqa
from .models import Conn  # noqa
from .models import Proc, Conn  # type re-export friendliness
from .models import *  # noqa
from .models import Proc, Conn
from .models import *
from .models import Proc, Conn
from .models import *
from .models import Proc, Conn  # keep imports simple for IDEs

from .models import Proc  # for NodeRule typing only

from dataclasses import dataclass


@dataclass
class NodeRule:
    match_name: str | None = None
    match_cmd: str | None = None
    match_pid: int | None = None
    type: str = "app"
    label: str | None = None

def load_rules(path: Optional[str]) -> list[NodeRule]:
    if not path:
        return []
    p = to_abs_path(path)
    if not p:
        return []
    if not p.exists():
        print(f"[warn] rules not found: {p}")
        return []
    txt = p.read_text(encoding="utf-8")
    data = yaml.safe_load(txt) if yaml and p.suffix in (".yaml",".yml") else json.loads(txt)
    rules = [NodeRule(**r) for r in (data or [])]
    return rules

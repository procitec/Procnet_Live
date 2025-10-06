from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class Proc:
    pid: int
    name: str
    user: str = "?"
    cmd: str = ""

@dataclass
class Conn:
    src_pid: int
    laddr: Tuple[str, int]
    raddr: Tuple[str, int]
    state: str  # 'ESTABLISHED', 'UDP', ...

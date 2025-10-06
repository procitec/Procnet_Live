from __future__ import annotations
from typing import Optional, Set
from ..config import DEFAULT_SERVICE_PORTS

def service_port(p1: int, p2: int, extra: Optional[Set[int]] = None) -> int:
    svcset = set(DEFAULT_SERVICE_PORTS)
    if extra: svcset |= set(extra)
    if p1 in svcset: return p1
    if p2 in svcset: return p2
    if p1 < 1024 <= p2: return p1
    if p2 < 1024 <= p1: return p2
    return p1 if p1 <= p2 else p2

def resolve_dst_pid(ip: str, port: int, listeners: dict[tuple[str,int], int]) -> int | None:
    if (ip, port) in listeners: return listeners[(ip, port)]
    for wildcard in ("0.0.0.0", "::"):
        if (wildcard, port) in listeners: return listeners[(wildcard, port)]
    if ip.startswith("127.") and ("127.0.0.1", port) in listeners:
        return listeners[("127.0.0.1", port)]
    if ip in ("::1",) and ("::", port) in listeners:
        return listeners[("::", port)]
    return None

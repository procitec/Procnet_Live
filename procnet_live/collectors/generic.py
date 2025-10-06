from __future__ import annotations
try:
    import psutil  # type: ignore
except Exception:
    psutil = None

from ..models import Proc, Conn

def collect() -> tuple[dict[int, Proc], list[Conn]]:
    procs: dict[int, Proc] = {}
    conns: list[Conn] = []
    if not psutil:
        return procs, conns
    for c in psutil.net_connections(kind='tcp'):
        if not c.pid or not c.raddr or not c.laddr: 
            continue
        procs.setdefault(c.pid, Proc(pid=c.pid, name="?", user="?", cmd=""))
        l = (c.laddr.ip if hasattr(c.laddr,'ip') else c.laddr[0], c.laddr.port if hasattr(c.laddr,'port') else c.laddr[1])
        r = (c.raddr.ip if hasattr(c.raddr,'ip') else c.raddr[0], c.raddr.port if hasattr(c.raddr,'port') else c.raddr[1])
        conns.append(Conn(src_pid=c.pid, laddr=l, raddr=r, state=str(c.status)))
    return procs, conns

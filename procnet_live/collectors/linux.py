from __future__ import annotations
from typing import Dict, List, Tuple
import subprocess, re
try:
    import psutil  # type: ignore
except Exception:
    psutil = None

from ..models import Proc, Conn

SS_RE = re.compile(r"^(?P<state>\S+)\s+\S+\s+\S+\s+(?P<laddr>[^\s]+)\s+(?P<raddr>[^\s]+)\s+.*users:\(\(")
PID_RE = re.compile(r"pid=(?P<pid>\d+),?\s*fd=\d+")
NAME_RE = re.compile(r'\"(?P<name>[^\"]+)\"')

def parse_addr(addr: str) -> tuple[str,int]:
    if addr.startswith("["):
        host, port = addr.rsplit(":", 1)
        return host.strip("[]"), int(port)
    if ":" in addr:
        host, port = addr.rsplit(":", 1)
        return host, int(port)
    return addr, 0

def collect() -> tuple[dict[int, Proc], list[Conn]]:
    procs: dict[int, Proc] = {}
    conns: list[Conn] = []
    try:
        out = subprocess.check_output(["ss","-tanpi"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return procs, conns
    for line in out.splitlines():
        m = SS_RE.match(line)
        if not m: continue
        state, l, r = m.group("state"), m.group("laddr"), m.group("raddr")
        mpid = PID_RE.search(line)
        pid = int(mpid.group("pid")) if mpid else None
        if not pid: continue
        name = None
        mname = NAME_RE.search(line)
        if mname: name = mname.group("name")
        if pid not in procs:
            procs[pid] = Proc(pid=pid, name=name or "?")
        conns.append(Conn(src_pid=pid, laddr=parse_addr(l), raddr=parse_addr(r), state=state))
    # enrich
    if psutil:
        for pid in list(procs.keys()):
            try:
                p = psutil.Process(pid)
                procs[pid].name = procs[pid].name or p.name()
                procs[pid].user = p.username()
                procs[pid].cmd = " ".join(p.cmdline())
            except Exception:
                pass
    return procs, conns

import re
import subprocess
from typing import Dict, List, Tuple, Optional

from ..models import Proc, Conn

SS_RE = re.compile(
    r"^(?P<state>\S+)\s+\S+\s+\S+\s+(?P<laddr>\S+)\s+(?P<raddr>\S+)\s+.*users:\(\(")
PID_RE = re.compile(r"pid=(?P<pid>\d+),?\s*fd=\d+")
NAME_RE = re.compile(r"\"(?P<name>[^\"]+)\"")

def _safe_int(s: str, default: int = 0) -> int:
    try:
        return int(s)
    except Exception:
        return default

def parse_addr(addr: str) -> Tuple[str, int]:
    """
    Unterstützt:
      - '1.2.3.4:5678'
      - '[::1]:443'
      - '0.0.0.0:*', '*:443', '*:*', '*'
    """
    if not addr or addr == '*':
        return ('*', 0)

    if addr.startswith('['):
        try:
            host, port = addr.rsplit(':', 1)
            host = host.strip('[]')
            if port == '*' or port == '':
                return (host or '::', 0)
            return (host or '::', _safe_int(port, 0))
        except Exception:
            return ('::', 0)

    if addr.startswith('*:'):
        _, port = addr.split(':', 1)
        return ('*', 0 if port == '*' else _safe_int(port, 0))

    if ':' in addr:
        host, port = addr.rsplit(':', 1)
        if port == '*' or port == '':
            return (host or '0.0.0.0', 0)
        return (host or '0.0.0.0', _safe_int(port, 0))

    return (addr, 0)

def collect() -> Tuple[Dict[int, Proc], List[Conn]]:
    procs: Dict[int, Proc] = {}
    conns: List[Conn] = []
    try:
        out = subprocess.check_output(["ss", "-tanpi"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return procs, conns

    for line in out.splitlines():
        m = SS_RE.match(line)
        if not m:
            continue

        state = m.group("state")
        l = m.group("laddr")
        r = m.group("raddr")

        if state.upper() == "LISTEN":
            continue

        mpid = PID_RE.search(line)
        pid: Optional[int] = int(mpid.group("pid")) if mpid else None
        if not pid:
            continue

        name = None
        mname = NAME_RE.search(line)
        if mname:
            name = mname.group("name")

        try:
            laddr = parse_addr(l)
            raddr = parse_addr(r)
        except Exception:
            continue

        if raddr[0] == '*' and raddr[1] == 0:
            continue

        if pid not in procs:
            procs[pid] = Proc(pid=pid, name=name or "?")

        conns.append(Conn(src_pid=pid, laddr=laddr, raddr=raddr, state=state))

    try:
        import psutil  # type: ignore
    except Exception:
        psutil = None

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

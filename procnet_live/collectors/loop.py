from __future__ import annotations
import platform, time
try:
    import psutil  # type: ignore
except Exception:
    psutil = None

from ..config import CFG
from ..models import Proc, Conn
from .windows import collect as windows_collect
from .linux import collect as linux_collect
from .generic import collect as generic_collect

def enrich_proc_info(pid: int) -> Proc:
    name = "?"; user = "?"; cmd = ""
    if psutil:
        try:
            p = psutil.Process(pid)
            name = p.name(); user = p.username()
            try:
                cmdline = p.cmdline()
                if cmdline: cmd = " ".join(cmdline)
            except Exception: cmd = ""
            if not cmd:
                try: cmd = p.exe() or name
                except Exception: cmd = name
        except Exception:
            pass
    return Proc(pid=pid, name=name, user=user, cmd=cmd)

def build_listeners() -> dict[tuple[str,int], int]:
    lst: dict[tuple[str,int], int] = {}
    if not psutil: return lst
    try:
        for lc in psutil.net_connections(kind='tcp'):
            if getattr(lc, 'status', '') != psutil.CONN_LISTEN:
                continue
            pid = lc.pid
            if not pid or not lc.laddr: continue
            lip = lc.laddr.ip if hasattr(lc.laddr,'ip') else lc.laddr[0]
            lpt = lc.laddr.port if hasattr(lc.laddr,'port') else lc.laddr[1]
            lst[(lip, lpt)] = pid
            if ':' in lip: lst[("::", lpt)] = pid
            else: lst[("0.0.0.0", lpt)] = pid
    except Exception:
        pass
    return lst

def collector_loop(cfg: CFG, snap, interval: float):
    while True:
        if platform.system() == 'Windows':
            procs, conns = windows_collect()
            # enrich each proc
            for pid in list(procs.keys()):
                procs[pid] = enrich_proc_info(pid)
        elif platform.system() == 'Linux':
            procs, conns = linux_collect()
        else:
            procs, conns = generic_collect()
        listeners = build_listeners()

        # Optionally include UDP (psutil only)
        if cfg.udp_enabled and psutil:
            try:
                for uc in psutil.net_connections(kind='udp'):
                    if not uc.pid or not uc.laddr or not uc.raddr:
                        continue
                    l = (uc.laddr.ip if hasattr(uc.laddr,'ip') else uc.laddr[0], uc.laddr.port if hasattr(uc.laddr,'port') else uc.laddr[1])
                    r = (uc.raddr.ip if hasattr(uc.raddr,'ip') else uc.raddr[0], uc.raddr.port if hasattr(uc.raddr,'port') else uc.raddr[1])
                    conns.append(Conn(src_pid=uc.pid, laddr=l, raddr=r, state='UDP'))
                    procs.setdefault(uc.pid, enrich_proc_info(uc.pid))
            except Exception:
                pass

        with snap.lock:
            snap.procs = procs
            snap.conns = conns
            snap.listeners = listeners
        time.sleep(interval)

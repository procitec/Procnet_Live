from __future__ import annotations
from typing import Dict, List, Tuple
import ctypes, socket, struct, ipaddress, platform
import ctypes.wintypes as wt

from ..models import Proc, Conn
from ..utils.net import ntohs16, ipv4_from_dword, ipv6_from_bytes

def enrich_proc_info(pid: int) -> Proc:
    # Lightweight; caller may replace
    return Proc(pid=pid, name="?", user="?", cmd="")

def collect() -> tuple[dict[int, Proc], list[Conn]]:
    if platform.system() != "Windows":
        return {}, []

    iphlpapi = ctypes.WinDLL('Iphlpapi.dll')
    AF_INET = 2
    AF_INET6 = 23
    TCP_TABLE_OWNER_PID_ALL = 5

    class MIB_TCPROW_OWNER_PID(ctypes.Structure):
        _fields_ = [("state", wt.DWORD), ("localAddr", wt.DWORD), ("localPort", wt.DWORD),
                    ("remoteAddr", wt.DWORD), ("remotePort", wt.DWORD), ("owningPid", wt.DWORD)]

    class MIB_TCPTABLE_OWNER_PID(ctypes.Structure):
        _fields_ = [("dwNumEntries", wt.DWORD), ("table", MIB_TCPROW_OWNER_PID * 1)]

    class IN6_ADDR(ctypes.Structure):
        _fields_ = [("Byte", wt.BYTE * 16)]

    class MIB_TCP6ROW_OWNER_PID(ctypes.Structure):
        _fields_ = [("localAddr", IN6_ADDR), ("localScopeId", wt.DWORD), ("localPort", wt.DWORD),
                    ("remoteAddr", IN6_ADDR), ("remoteScopeId", wt.DWORD), ("remotePort", wt.DWORD),
                    ("state", wt.DWORD), ("owningPid", wt.DWORD)]

    class MIB_TCP6TABLE_OWNER_PID(ctypes.Structure):
        _fields_ = [("dwNumEntries", wt.DWORD), ("table", MIB_TCP6ROW_OWNER_PID * 1)]

    GetExtendedTcpTable = iphlpapi.GetExtendedTcpTable
    GetExtendedTcpTable.restype = wt.DWORD

    def _port_from_dword(d: int) -> int:
        return ntohs16(d)

    def _ipv4_str(dw: int) -> str:
        return ipv4_from_dword(dw)

    def _ipv6_str(addr: IN6_ADDR) -> str:
        return ipv6_from_bytes(bytes(addr.Byte))

    TCP_STATE = {
        1:"CLOSED",2:"LISTEN",3:"SYN_SENT",4:"SYN_RECEIVED",5:"ESTABLISHED",
        6:"FIN_WAIT1",7:"FIN_WAIT2",8:"CLOSE_WAIT",9:"CLOSING",10:"LAST_ACK",11:"TIME_WAIT",12:"DELETE_TCB"
    }

    conns: list[Conn] = []

    # IPv4
    size = wt.ULONG(0)
    GetExtendedTcpTable(None, ctypes.byref(size), False, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0)
    buf = ctypes.create_string_buffer(size.value)
    if GetExtendedTcpTable(buf, ctypes.byref(size), False, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0) == 0:
        table = ctypes.cast(buf, ctypes.POINTER(MIB_TCPTABLE_OWNER_PID)).contents
        rows = ctypes.cast(ctypes.addressof(table.table), ctypes.POINTER(MIB_TCPROW_OWNER_PID * table.dwNumEntries)).contents
        for r in rows:
            if TCP_STATE.get(r.state) == "LISTEN":
                continue
            laddr = (_ipv4_str(r.localAddr), _port_from_dword(r.localPort))
            raddr = (_ipv4_str(r.remoteAddr), _port_from_dword(r.remotePort))
            conns.append(Conn(src_pid=int(r.owningPid), laddr=laddr, raddr=raddr, state=TCP_STATE.get(r.state, str(r.state))))

    # IPv6
    size6 = wt.ULONG(0)
    GetExtendedTcpTable(None, ctypes.byref(size6), False, AF_INET6, TCP_TABLE_OWNER_PID_ALL, 0)
    buf6 = ctypes.create_string_buffer(size6.value)
    if GetExtendedTcpTable(buf6, ctypes.byref(size6), False, AF_INET6, TCP_TABLE_OWNER_PID_ALL, 0) == 0:
        table6 = ctypes.cast(buf6, ctypes.POINTER(MIB_TCP6TABLE_OWNER_PID)).contents
        rows6 = ctypes.cast(ctypes.addressof(table6.table), ctypes.POINTER(MIB_TCP6ROW_OWNER_PID * table6.dwNumEntries)).contents
        for r in rows6:
            if TCP_STATE.get(r.state) == "LISTEN":
                continue
            laddr = (_ipv6_str(r.localAddr), _port_from_dword(r.localPort))
            raddr = (_ipv6_str(r.remoteAddr), _port_from_dword(r.remotePort))
            conns.append(Conn(src_pid=int(r.owningPid), laddr=laddr, raddr=raddr, state=TCP_STATE.get(r.state, str(r.state))))

    # Enrich procs set (only those PIDs that appear)
    pids = sorted({c.src_pid for c in conns})
    procs: dict[int, Proc] = {pid: Proc(pid=pid, name="?", user="?", cmd="") for pid in pids}
    return procs, conns

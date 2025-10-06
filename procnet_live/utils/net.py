from __future__ import annotations
import socket, struct, ipaddress, ctypes

def ntohs16(v: int) -> int:
    return socket.ntohs(v & 0xFFFF)

def ipv4_from_dword(dw: int) -> str:
    return socket.inet_ntoa(struct.pack('<I', ctypes.c_uint32(dw).value))

def ipv6_from_bytes(b: bytes) -> str:
    try:
        return socket.inet_ntop(socket.AF_INET6, b)
    except AttributeError:
        return str(ipaddress.IPv6Address(b))

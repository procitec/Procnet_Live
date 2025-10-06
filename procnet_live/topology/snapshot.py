from __future__ import annotations
import threading
from ..models import Proc, Conn
from ..rules import NodeRule

class Snapshot:
    def __init__(self):
        self.lock = threading.Lock()
        self.procs: dict[int, Proc] = {}
        self.conns: list[Conn] = []
        self.rules: list[NodeRule] = []
        self.listeners: dict[tuple[str,int], int] = {}
        self.edge_cache: dict[str, dict] = {}
        self.edge_ttl: float = 15.0

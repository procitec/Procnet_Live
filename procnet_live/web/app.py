from __future__ import annotations
from flask import Flask, Response, jsonify, request, send_from_directory
try:
    import orjson as _oj
    def dumps(obj): return _oj.dumps(obj).decode()
except Exception:
    import json as _json
    def dumps(obj): return _json.dumps(obj)

from ..config import CFG
from ..rules import load_rules
from .ui import render_html

def create_app(cfg: CFG, snap) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return Response(render_html(cfg.udp_enabled), mimetype="text/html")

    @app.get("/api/graph")
    def api_graph():
        with snap.lock:
            from ..topology.graph_build import snapshot_to_graph
            return Response(dumps(snapshot_to_graph(snap, cfg)), mimetype="application/json")

    @app.post("/api/reload_rules")
    def api_reload_rules():
        path = request.json.get("path") if request.is_json else request.args.get("path")
        snap.rules = load_rules(path)
        return jsonify({"ok": True, "rules": len(snap.rules)})

    @app.get("/assets/<path:filename>")
    def assets(filename):
        if cfg.icons_dir:
            return send_from_directory(str(cfg.icons_dir), filename)
        return Response(status=404)

    return app

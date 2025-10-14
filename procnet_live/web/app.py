from __future__ import annotations
from flask import Flask, Response, jsonify, request, send_from_directory
from flask import Blueprint, make_response, current_app
import json as stdjson  # <- immer verfügbar

try:
    import orjson as _oj
    def dumps(obj): return _oj.dumps(obj).decode()
except Exception:
    _oj = None
    def dumps(obj): return stdjson.dumps(obj)

from ..config import CFG
from ..rules import load_rules
from .ui import render_html
from pathlib import Path

vendor_bp = Blueprint("vendor", __name__)

@vendor_bp.route("/vendor/<path:filename>")
def vendor(filename):
    base = Path(__file__).parent / "vendor"
    resp = send_from_directory(base, filename, conditional=True, etag=True)
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    current_app.logger.info("vis-network vendor served: %s", filename)
    return resp

@vendor_bp.route("/vendor/manifest.json")
def vendor_manifest():
    base = Path(__file__).parent / "vendor" / "manifest.json"
    if not base.exists():
        # no manifest yet (e.g., prepare script not run)
        data = {"vis_network_version": None, "js_file": None}
        current_app.logger.warning("vis-network manifest NOT FOUND at %s (will default to fallback)", base.resolve())
    else:
        data = stdjson.loads(base.read_text(encoding="utf-8"))
        current_app.logger.info("vis-network manifest: %s", data)
    resp = make_response(stdjson.dumps(data))
    # Manifest should NOT be cached, so changes are seen immediately
    resp.headers["Content-Type"] = "application/json"
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp

def create_app(cfg: CFG, snap) -> Flask:
    app = Flask(__name__)
    app.register_blueprint(vendor_bp)

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

from __future__ import annotations
from typing import Dict, List, Tuple
from ..config import CFG, PORT_CLASS, DEFAULT_EDGE_COLOR, NODE_TYPE_STYLE, UDP_EDGE_COLOR
from ..rules import NodeRule
from ..models import Proc, Conn
from .heuristics import service_port, resolve_dst_pid

import re

def node_type_for(proc: Proc, rules: list[NodeRule]) -> tuple[str,str]:
    for r in rules:
        if r.match_pid and r.match_pid == proc.pid:
            return r.type, (r.label or proc.name)
        if r.match_name:
            if r.match_name.startswith('/') and r.match_name.endswith(('/i','/I')):
                pattern = r.match_name[1:-2]
                if re.search(pattern, proc.name or '', flags=re.IGNORECASE):
                    return r.type, (r.label or proc.name)
            elif r.match_name.startswith('/') and r.match_name.endswith('/'):
                if re.search(r.match_name.strip('/'), proc.name or ''):
                    return r.type, (r.label or proc.name)
            elif r.match_name == proc.name:
                return r.type, (r.label or proc.name)
        if r.match_cmd:
            hay = f"{proc.cmd or ''} {proc.name or ''}"
            m = r.match_cmd
            if m.startswith('/') and m.endswith(('/i','/I')):
                pattern = m[1:-2]
                if re.search(pattern, hay, flags=re.IGNORECASE):
                    return r.type, (r.label or proc.name)
            elif m.startswith('/') and m.endswith('/'):
                if re.search(m.strip('/'), hay):
                    return r.type, (r.label or proc.name)
            else:
                if m.lower() in hay.lower():
                    return r.type, (r.label or proc.name)
    return 'app', (proc.name or f'pid {proc.pid}')

# --- Icon/Shape Fallback: PNG des Typs, sonst service.png, sonst Icon ----
def _shape_image_for_type(ntype: str, cfg: CFG) -> tuple[str, str|None]:
    if cfg.icons_dir:
        fn = cfg.icons_map.get(ntype)
        if fn:
            return 'image', f"/assets/{fn}"
        fn_service = cfg.icons_map.get('service')
        if fn_service:
            return 'image', f"/assets/{fn_service}"
    return 'icon', None

def snapshot_to_graph(snap, cfg: CFG) -> dict:
    now_nodes = {}
    for pid, proc in snap.procs.items():
        ntype, label = node_type_for(proc, snap.rules)
        style = NODE_TYPE_STYLE.get(ntype, NODE_TYPE_STYLE['app'])
        shape, img = _shape_image_for_type(ntype, cfg)
        now_nodes[str(pid)] = {
            'id': str(pid),
            'label': f"{label}\nPID {pid}",
            'title': proc.cmd,
            'color': style['color'],
            'icon': style['icon'],
            'type': ntype,
            'shape': shape,
            'image': img
        }
    ext_nodes = {}
    edges = {}
    index = {(c.laddr, c.raddr): c for c in snap.conns}
    edge_seen = set()

    for c in snap.conns:
        peer = index.get((c.raddr, c.laddr))
        if not peer: continue
        pid1, pid2 = c.src_pid, peer.src_pid
        if pid1 == pid2: continue
        # nur cfg.svc_ports berücksichtigen
        svc = service_port(c.laddr[1], c.raddr[1], cfg.svc_ports)
        a, b = (pid1, pid2) if pid1 < pid2 else (pid2, pid1)
        norm = (a, b, svc)
        if norm in edge_seen: continue
        server_pid = pid1 if c.laddr[1] == svc else (pid2 if peer.laddr[1] == svc else pid2)
        client_pid = pid2 if server_pid == pid1 else pid1
        client_port = c.laddr[1] if client_pid == c.src_pid else peer.laddr[1]
        server_port = svc
        client_ip   = c.laddr[0] if client_pid == c.src_pid else peer.laddr[0]
        server_ip   = c.laddr[0] if server_pid == c.src_pid else peer.laddr[0]
        _, color = PORT_CLASS.get(server_port, ('other', DEFAULT_EDGE_COLOR))
        edge_id = f"{client_pid}->{server_pid}:{server_port}"
        edges[edge_id] = {
            'id': edge_id,
            'from': str(client_pid), 'to': str(server_pid),
            'label': f":{client_port}→:{server_port}",
            'title': f"{client_ip}:{client_port} ↔ {server_ip}:{server_port} | TCP ESTABLISHED :{server_port}",
            'color': color,
            'state': 'ESTABLISHED',
            'proto': 'TCP',
        }
        edge_seen.add(norm)

    # Count parallel sockets (approx. same as canvas)
    from collections import defaultdict
    pair_counts = defaultdict(int)
    for c2 in snap.conns:
        peer2 = index.get((c2.raddr, c2.laddr))
        if not peer2: continue
        if c2.src_pid == peer2.src_pid: continue
        svc2 = service_port(c2.laddr[1], c2.raddr[1], cfg.svc_ports)
        server2 = c2.src_pid if c2.laddr[1] == svc2 else peer2.src_pid
        client2 = peer2.src_pid if server2 == c2.src_pid else c2.src_pid
        if c2.src_pid < peer2.src_pid:
            pair_counts[(client2, server2, svc2)] += 1
    for (cl, sv, sp), cnt in pair_counts.items():
        eid = f"{cl}->{sv}:{sp}"
        if eid in edges and cnt > 1:
            edges[eid]['label'] = f"{edges[eid]['label']} ×{cnt}"
            edges[eid]['title'] = f"{edges[eid]['title']} | sockets: {cnt}"

    # Fallbacks: external/listeners
    if not cfg.p2p_only:
        for c in snap.conns:
            svc = service_port(c.laddr[1], c.raddr[1], cfg.svc_ports)
            peer = index.get((c.raddr, c.laddr))
            if peer:
                a,b = (c.src_pid, peer.src_pid)
                na, nb = (a,b) if a < b else (b,a)
                if (na, nb, svc) in edge_seen:
                    continue
            dst_pid = resolve_dst_pid(c.raddr[0], c.raddr[1], snap.listeners)
            _, color = PORT_CLASS.get(c.raddr[1], ('other', DEFAULT_EDGE_COLOR))
            if dst_pid is not None:
                edge_id = f"{c.src_pid}->{dst_pid}:{c.raddr[1]}"
                if str(dst_pid) not in now_nodes:
                    # Typ aus Regeln ableiten; Default 'app'; Service-Image-Fallback nutzen
                    proc = snap.procs.get(dst_pid, Proc(pid=dst_pid, name=""))
                    ntype, label = node_type_for(proc, snap.rules)
                    ntype = ntype or 'app'
                    style = NODE_TYPE_STYLE.get(ntype, NODE_TYPE_STYLE['app'])
                    shape, img = _shape_image_for_type(ntype, cfg)
                    title = (proc.cmd or proc.name or f"PID {dst_pid}")
                    now_nodes[str(dst_pid)] = {
                        'id': str(dst_pid),
                        'label': (f"{label}\nPID {dst_pid}" if label else f"PID {dst_pid}"),
                        'title': title,
                        'color': style['color'],
                        'icon': style['icon'],
                        'type': ntype,
                        'shape': shape,
                        'image': img
                    }
                edges[edge_id] = {
                    'id': edge_id,
                    'from': str(c.src_pid), 'to': str(dst_pid),
                    'label': f":{c.laddr[1]}→:{c.raddr[1]}",
                    'title': f"{c.laddr[0]}:{c.laddr[1]} → local:{c.raddr[1]} | " + ("UDP " if c.state=='UDP' else "TCP ") + c.state,
                    'color': (UDP_EDGE_COLOR if c.state=='UDP' else color),
                    'state': c.state,
                    'proto': ('UDP' if c.state=='UDP' else 'TCP'),
                }
            else:
                dst = f"{c.raddr[0]}:{c.raddr[1]}"
                if dst not in ext_nodes:
                    # Für external: wenn external.png fehlt, bleibt 'icon' (hier kein dot-Fall vorhanden)
                    shape_ext = 'image' if cfg.icons_dir and cfg.icons_map.get('external') else 'icon'
                    img_ext = (f"/assets/{cfg.icons_map.get('external')}" if cfg.icons_dir and cfg.icons_map.get('external') else None)
                    ext_nodes[dst] = {
                        'id': dst,
                        'label': dst,
                        'title': 'remote endpoint',
                        'color': NODE_TYPE_STYLE['external']['color'],
                        'icon': NODE_TYPE_STYLE['external']['icon'],
                        'type': 'external',
                        'shape': shape_ext,
                        'image': img_ext
                    }
                edge_id = f"{c.src_pid}->{dst}:{c.raddr[1]}"
                edges[edge_id] = {
                    'id': edge_id,
                    'from': str(c.src_pid), 'to': dst,
                    'label': f":{c.laddr[1]}→:{c.raddr[1]}",
                    'title': f"{c.laddr[0]}:{c.laddr[1]} → {c.raddr[0]}:{c.raddr[1]} | " + ("UDP " if c.state=='UDP' else "TCP ") + c.state,
                    'color': (UDP_EDGE_COLOR if c.state=='UDP' else color),
                    'state': c.state,
                    'proto': ('UDP' if c.state=='UDP' else 'TCP'),
                }

    # TTL cache: fade stale
    now = __import__('time').time()
    for eid, e in list(edges.items()):
        snap.edge_cache[eid] = {'edge': e, 'last_seen': now}
    for eid, entry in list(snap.edge_cache.items()):
        if eid in edges: continue
        if now - entry['last_seen'] <= snap.edge_ttl:
            stale = dict(entry['edge'])
            stale['id'] = eid
            stale['state'] = stale.get('state','STALE')
            stale['label'] = stale.get('label','')
            stale['color'] = 'rgba(200,200,200,0.7)'
            stale['dashes'] = False
            stale['width'] = 2.5
            stale['stale'] = True
            edges[eid] = stale
        else:
            del snap.edge_cache[eid]

    # ensure all edge endpoints exist
    for e in edges.values():
        if e['from'] not in now_nodes and str(e['from']).isdigit():
            shape_from, img_from = _shape_image_for_type('app', cfg)
            now_nodes[str(e['from'])] = {
                'id': str(e['from']),
                'label': f"PID {e['from']}",
                'title': 'process',
                'color': NODE_TYPE_STYLE['app']['color'],
                'icon': NODE_TYPE_STYLE['app']['icon'],
                'type': 'app',
                'shape': shape_from,
                'image': img_from
            }
        if e['to'] not in now_nodes:
            if str(e['to']).isdigit():
                pid_to = int(e['to'])
                proc_to = snap.procs.get(pid_to, Proc(pid=pid_to, name=""))
                ntype_to, label_to = node_type_for(proc_to, snap.rules)
                ntype_to = ntype_to or 'app'
                style_to = NODE_TYPE_STYLE.get(ntype_to, NODE_TYPE_STYLE['app'])
                shape_to, img_to = _shape_image_for_type(ntype_to, cfg)
                now_nodes[str(e['to'])] = {
                    'id': str(e['to']),
                    'label': (f"{label_to}\nPID {pid_to}" if label_to else f"PID {pid_to}"),
                    'title': (proc_to.cmd or proc_to.name or 'process'),
                    'color': style_to['color'],
                    'icon': style_to['icon'],
                    'type': ntype_to,
                    'shape': shape_to,
                    'image': img_to
                }
            else:
                if not cfg.p2p_only:
                    shape_ext = 'image' if cfg.icons_dir and cfg.icons_map.get('external') else 'icon'
                    img_ext = (f"/assets/{cfg.icons_map.get('external')}" if cfg.icons_dir and cfg.icons_map.get('external') else None)
                    now_nodes[e['to']] = {
                        'id': e['to'],
                        'label': e['to'],
                        'title': 'remote endpoint',
                        'color': NODE_TYPE_STYLE['external']['color'],
                        'icon': NODE_TYPE_STYLE['external']['icon'],
                        'type': 'external',
                        'shape': shape_ext,
                        'image': img_ext
                    }

    # layout: curved multi-edges
    pairs = {}
    for e in edges.values():
        key = (e['from'], e['to'])
        pairs.setdefault(key, []).append(e)
    for key, elist in pairs.items():
        if len(elist) <= 1:
            elist[0]['smooth'] = {'enabled': True, 'type': 'continuous'}
            continue
        elist.sort(key=lambda x: int(x['id'].split(':')[-1]) if ':' in x['id'] and x['id'].split(':')[-1].isdigit() else 0)
        offsets = [0.0, 0.15, -0.15, 0.3, -0.3, 0.45, -0.45, 0.6, -0.6]
        for i, e in enumerate(elist):
            if i < len(offsets): o = offsets[i]
            else:
                step = 0.15 * ((i // 2) + 1)
                o = step if i % 2 else -step
            e['smooth'] = {'enabled': True, 'type': ('curvedCW' if o >= 0 else 'curvedCCW'), 'roundness': abs(o)}

    all_nodes = list(now_nodes.values()) + ([] if cfg.p2p_only else list(ext_nodes.values()))
    return {'nodes': all_nodes, 'edges': list(edges.values())}

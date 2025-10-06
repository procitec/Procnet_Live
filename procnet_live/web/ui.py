HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Process TCP Map</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body { background:#14181d; color:#e8eaed; font-family: ui-sans-serif,system-ui,Segoe UI,Arial; }
    #net { height: 90vh; border: 1px solid #2a2f36; border-radius: 12px; }
  </style>
</head>
<body>
  <h2>Process ↔ TCP Map (Live)</h2>
  <div id="net"></div>
  <script>
  const container = document.getElementById('net');
  const nodes = new vis.DataSet([]);
  const edges = new vis.DataSet([]);
  const network = new vis.Network(container, {nodes, edges}, {
    physics:{stabilization:true, barnesHut:{gravitationalConstant:-20000, centralGravity:0.18, springLength:180}},
    nodes:{shadow:true, font:{color:'#e8eaed'}},
    edges:{arrows:{to:{enabled:true}}, smooth:{enabled:true, type:'continuous'}, shadow:true, font:{align:'top'}}
  });
  network.once('stabilized', ()=>{ network.storePositions(); });
  const dashByState = {'SYN_SENT':[2,6],'SYN_RECEIVED':[6,6],'TIME_WAIT':[10,6],'CLOSE_WAIT':[4,6]};
  function applyDiff(newNodes, newEdges){
    const existingN = new Set(nodes.getIds());
    const incomingN = new Set(newNodes.map(n=>n.id));
    newNodes.forEach(n=>{
      if(n.shape === 'icon') {
        n.icon = {face:'FontAwesome', code:n.icon, color:n.color};
      }
      if(nodes.get(n.id)) nodes.update(n); else nodes.add(n);
    });
    existingN.forEach(id=>{ if(!incomingN.has(id)) nodes.remove(id); });
    const existingE = new Set(edges.getIds());
    const incomingE = new Set(newEdges.map(e=>e.id));
    newEdges.forEach(e=>{
      if (e.stale) { e.width = e.width || 2.5; e.shadow = true; }
      e.dashes = e.stale ? false : (dashByState[e.state] || false);
      if(edges.get(e.id)) edges.update(e); else edges.add(e);
    });
    existingE.forEach(id=>{ if(!incomingE.has(id)) edges.remove(id); });
  }
  async function refresh(){
    try{
      const r = await fetch('/api/graph');
      const data = await r.json();
      applyDiff(data.nodes, data.edges);
    }catch(e){ console.error(e); }
  }
  setInterval(refresh, 1500);
  refresh();
  </script>
</body>
</html>
"""

def render_html(udp_enabled: bool) -> str:
    title = "Process TCP/UDP Map" if udp_enabled else "Process TCP Map"
    header = "Process ↔ TCP/UDP Map (Live)" if udp_enabled else "Process ↔ TCP Map (Live)"
    html = HTML.replace("<title>Process TCP Map</title>", f"<title>{title}</title>")
    html = html.replace(">Process ↔ TCP Map (Live)<", f">{header}<")
    return html

import { useState, useEffect, useRef } from "react"
import ForceGraph3D from "react-force-graph-3d"
import SpriteText from "three-spritetext"
import * as THREE from "three"
import axios from "axios"
import "./index.css"

const API = import.meta.env.VITE_API_URL || (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" ? "http://127.0.0.1:8000" : "https://ordertocash-backend.onrender.com")

/* ── Gemini diamond SVG ── */
const DiamondIcon = ({ size = 14, white = false }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      d="M12 2C12 7 17 12 22 12C17 12 12 17 12 22C12 17 7 12 2 12C7 12 12 7 12 2Z"
      fill={white ? "#fff" : "url(#gemi)"}
    />
    {!white && (
      <defs>
        <linearGradient id="gemi" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#1A73E8" />
          <stop offset="100%" stopColor="#A142F4" />
        </linearGradient>
      </defs>
    )}
  </svg>
)

/* ── GitHub Octocat-like logo ── */
const OctoLogo = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="#c9d1d9">
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.44 9.8 8.2 11.38.6.11.82-.26.82-.58v-2.03c-3.34.72-4.04-1.61-4.04-1.61-.54-1.38-1.33-1.75-1.33-1.75-1.09-.74.08-.73.08-.73 1.2.09 1.84 1.24 1.84 1.24 1.07 1.83 2.8 1.3 3.49 1 .1-.78.42-1.3.76-1.6-2.67-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.13-.3-.54-1.52.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 3-.4c1.02 0 2.04.14 3 .4 2.28-1.55 3.29-1.23 3.29-1.23.66 1.66.25 2.88.12 3.18.77.84 1.24 1.91 1.24 3.22 0 4.61-2.81 5.63-5.48 5.92.43.37.81 1.1.81 2.22v3.29c0 .32.22.7.82.58C20.56 21.8 24 17.3 24 12c0-6.63-5.37-12-12-12Z" />
  </svg>
)

/* ── Node color map ── */
const NODE_COLORS = {
  Orders:     "#1A73E8",
  Deliveries: "#3fb950",
  Invoices:   "#A142F4",
  Payments:   "#58a6ff",
  Customers:  "#f78166",
  Journal:    "#d2a8ff",
}

const getNodeColor = (n) => NODE_COLORS[n.type] || "#8b949e"

/* ══════════════════════════════════════════════════════════ */
export default function App() {
  const [graph,          setGraph]          = useState({ nodes: [], links: [] })
  const [popupData,      setPopupData]      = useState(null)
  const [messages,       setMessages]       = useState([
    { role: "ai", text: "Hello! I'm your Order-to-Cash AI assistant. Ask me anything about orders, invoices, payments, deliveries, or customers." }
  ])
  const [input,          setInput]          = useState("")
  const [loading,        setLoading]        = useState(false)
  const [highlightNodes, setHighlightNodes] = useState(new Set())
  const [chatHidden,     setChatHidden]     = useState(false)
  const [showLabels,     setShowLabels]     = useState(true)
  const [analytics,      setAnalytics]      = useState(null)

  const bottomRef = useRef(null)
  const fgRef     = useRef(null)

  useEffect(() => {
    axios.get(`${API}/graph`).then(r => setGraph(r.data)).catch(() => {})
    axios.get(`${API}/analytics`).then(r => setAnalytics(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const send = async () => {
    if (!input.trim() || loading) return
    const q = input.trim()
    setInput("")
    setLoading(true)
    setMessages(m => [...m, { role: "user", text: q }])

    try {
      const r = await axios.post(`${API}/query`, { question: q })
      setMessages(m => [...m, { role: "ai", text: r.data.answer }])

      const hn = r.data.highlight_nodes || []
      if (hn.length > 0) {
        setHighlightNodes(new Set(hn))
        const target = graph.nodes.find(n => hn.includes(n.id))
        if (target && fgRef.current) {
          const d = 1 + 100 / Math.hypot(target.x, target.y, target.z)
          fgRef.current.cameraPosition(
            { x: target.x * d, y: target.y * d, z: target.z * d },
            target, 1000
          )
        }
      } else {
        setHighlightNodes(new Set())
      }

      if (r.data.data?.length > 0) {
        setPopupData({ title: hn.length > 0 ? "Record Details" : "Query Results", rows: r.data.data })
      } else {
        setPopupData(null)
      }
    } catch {
      setMessages(m => [...m, { role: "ai", text: "⚠️ Could not reach the backend. Make sure the server is running." }])
    }
    setLoading(false)
  }

  const handleKey = e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send() }

  /* ── KPI data ── */
  const kpis = analytics ? [
    { label: "Orders",    value: analytics.total_orders,    color: "#1A73E8", icon: "📦" },
    { label: "Customers", value: analytics.total_customers, color: "#f78166", icon: "👥" },
    { label: "Invoices",  value: analytics.total_invoices,  color: "#A142F4", icon: "🧾" },
    { label: "Payments",  value: analytics.total_payments,  color: "#58a6ff", icon: "💳" },
    { label: "Revenue",   value: `$${(analytics.total_revenue || 0).toLocaleString()}`, color: "#3fb950", icon: "💰" },
  ] : []

  return (
    <div className="app-wrapper">

      {/* ════════════ TOP NAV ════════════ */}
      <nav className="top-nav">
        <div className="nav-brand">
          <div className="nav-logo-box">
            <DiamondIcon size={18} white />
          </div>
          <OctoLogo />
          <div className="nav-path">
            <span className="nav-org">OrderFlow-AI</span>
            <span className="nav-sep">/</span>
            <span className="nav-repo">Order to Cash</span>
          </div>
          <div className="nav-badge">
            <span className="pulse-dot" />
            Live
          </div>
        </div>

        <div className="nav-actions">
          <div className="nav-ai-label">
            <DiamondIcon size={16} />
            <span style={{ fontSize: "12px", color: "#8b949e" }}>AI Powered</span>
          </div>
          <button className="btn" onClick={() => setChatHidden(h => !h)}>
            {chatHidden ? "⊞ Chat" : "⊟ Chat"}
          </button>
          <button className="btn" onClick={() => setShowLabels(s => !s)}>
            {showLabels ? "Hide Labels" : "Show Labels"}
          </button>
        </div>
      </nav>

      {/* ════════════ KPI GRID ════════════ */}
      {analytics && (
        <div className="kpi-grid">
          {kpis.map(k => (
            <div
              key={k.label}
              className="kpi-card"
              style={{ "--kpi-color": k.color }}
            >
              <div className="kpi-header">
                <span className="kpi-label">{k.label}</span>
                <span className="kpi-icon">{k.icon}</span>
              </div>
              <div className="kpi-value">{k.value ?? "—"}</div>
              <div className="kpi-sub">Updated in real-time</div>
            </div>
          ))}
        </div>
      )}

      {/* ════════════ GRAPH LEGEND ════════════ */}
      <div className="legend-row">
        <span className="legend-label">Node Types:</span>
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="legend-item">
            <div className="legend-dot" style={{ background: color }} />
            <span>{type}</span>
          </div>
        ))}
      </div>

      {/* ════════════ WORKSPACE ════════════ */}
      <div className="workspace-row">

        {/* ── GRAPH ── */}
        <div className="graph-panel">
          <div className="graph-overlay-title">// 3D Process Graph · Drag to Rotate · Scroll to Zoom</div>

          <ForceGraph3D
            ref={fgRef}
            graphData={graph}
            backgroundColor="#0d1117"
            nodeLabel={null}
            onEngineStop={() => fgRef.current?.zoomToFit(800, 80)}
            nodeThreeObject={node => {
              const color       = getNodeColor(node)
              const isHl        = highlightNodes.has(node.id)
              const isFaded     = highlightNodes.size > 0 && !isHl
              const group       = new THREE.Group()

              const geo  = new THREE.SphereGeometry(isHl ? 8 : 5, 32, 32)
              const mat  = new THREE.MeshStandardMaterial({
                color:            isHl ? "#ffffff" : color,
                emissive:         color,
                emissiveIntensity: isHl ? 1.0 : 0.3,
                transparent:      true,
                opacity:          isFaded ? 0.1 : 1,
              })
              group.add(new THREE.Mesh(geo, mat))

              if (isHl) {
                const ring = new THREE.Mesh(
                  new THREE.RingGeometry(10, 11, 32),
                  new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.5, side: THREE.DoubleSide })
                )
                group.add(ring)
              }

              if (!isFaded && showLabels) {
                const sprite = new SpriteText(node.type || "")
                sprite.color      = isHl ? "#ffffff" : "#8b949e"
                sprite.textHeight = 4.5
                sprite.position.set(0, 13, 0)
                group.add(sprite)
              }
              return group
            }}
            linkWidth={link => {
              if (highlightNodes.size > 0) {
                const s = typeof link.source === "object" ? link.source.id : link.source
                const t = typeof link.target === "object" ? link.target.id : link.target
                return highlightNodes.has(s) || highlightNodes.has(t) ? 1.8 : 0.1
              }
              return 0.5
            }}
            linkColor={link => {
              if (highlightNodes.size > 0) {
                const s = typeof link.source === "object" ? link.source.id : link.source
                const t = typeof link.target === "object" ? link.target.id : link.target
                return highlightNodes.has(s) || highlightNodes.has(t)
                  ? "rgba(26,115,232,0.8)"
                  : "rgba(255,255,255,0.02)"
              }
              return "rgba(139,148,158,0.18)"
            }}
          />

          {/* POPUP */}
          {popupData && (
            <div className="popup-card">
              <div className="popup-title">
                <DiamondIcon size={14} />
                {popupData.title}
              </div>
              {popupData.rows.slice(0, 4).map((row, i) => (
                <div key={i} className="popup-section">
                  {Object.entries(row).slice(0, 8).map(([k, v]) => (
                    <div key={k} className="popup-row">
                      <span className="popup-key">{k}:</span>
                      <span className="popup-val">{String(v)}</span>
                    </div>
                  ))}
                </div>
              ))}
              <button className="popup-close" onClick={() => setPopupData(null)}>✕ Close</button>
            </div>
          )}
        </div>

        {/* ── CHAT PANEL ── */}
        {!chatHidden && (
          <div className="chat-panel">
            {/* Header */}
            <div className="chat-header">
              <div className="chat-avatar">
                <DiamondIcon size={18} white />
              </div>
              <div>
                <div className="chat-title">OrderFlow AI</div>
                <div className="chat-subtitle">// ask · explore · analyze</div>
              </div>
            </div>

            {/* Messages */}
            <div className="chat-messages">
              {messages.map((m, i) => (
                <div key={i} className="msg-group">
                  {m.role === "ai" ? (
                    <>
                      <div className="msg-meta">
                        <div className="msg-ai-dot">
                          <DiamondIcon size={10} white />
                        </div>
                        <span>OrderFlow AI</span>
                      </div>
                      <div className="msg-bubble-ai">{m.text}</div>
                    </>
                  ) : (
                    <>
                      <div className="msg-meta msg-meta-right">
                        <span>You</span>
                        <span style={{
                          width: "18px", height: "18px", borderRadius: "50%",
                          background: "#21262d", border: "1px solid #30363d",
                          display: "flex", alignItems: "center", justifyContent: "center",
                          fontSize: "10px"
                        }}>👤</span>
                      </div>
                      <div className="msg-bubble-user">{m.text}</div>
                    </>
                  )}
                </div>
              ))}

              {/* Thinking indicator — Claude dots */}
              {loading && (
                <div className="msg-group">
                  <div className="msg-meta">
                    <div className="msg-ai-dot">
                      <DiamondIcon size={10} white />
                    </div>
                    <span>Thinking…</span>
                  </div>
                  <div className="msg-bubble-ai">
                    <div className="typing-dots">
                      {[0, 1, 2].map(i => (
                        <div
                          key={i}
                          className="typing-dot"
                          style={{ animation: `dotBounce 1.2s ease-in-out ${i * 0.18}s infinite` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="chat-input-area">
              <div className="chat-composer">
                <textarea
                  className="chat-textarea"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder="Ask about orders, invoices, payments… (Ctrl+Enter to send)"
                />
                <div className="chat-composer-bar">
                  <span className="chat-hint">Ctrl+Enter to send</span>
                  <button
                    className="btn btn-primary"
                    onClick={send}
                    disabled={loading || !input.trim()}
                    style={{ padding: "7px 18px", fontSize: "13px" }}
                  >
                    {loading ? "Thinking…" : "Send ↑"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ════════════ FOOTER ════════════ */}
      <footer className="footer">
        <div>
          <div className="footer-brand">OrderFlow-AI Analytics Platform</div>
          <div className="footer-desc">Intelligent Order-to-Cash Process Visualization · Powered by AI</div>
        </div>
        <div className="footer-tags">
          <span className="footer-tag tag-blue">Real-time Insights</span>
          <span className="footer-tag tag-green">AI Analytics</span>
          <span className="footer-tag tag-purple">3D Visualization</span>
        </div>
      </footer>

    </div>
  )
}

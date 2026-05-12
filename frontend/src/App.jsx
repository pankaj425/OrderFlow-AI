import { useState, useEffect, useRef } from "react"
import ForceGraph3D from "react-force-graph-3d"
import SpriteText from "three-spritetext"
import * as THREE from "three"
import axios from "axios"

const API = "http://127.0.0.1:8000"

export default function App() {
  const [graph, setGraph] = useState({ nodes: [], links: [] })
  const [popupData, setPopupData] = useState(null)

  const [messages, setMessages] = useState([
    {
      role: "ai",
      text: "Hi! I can help you analyze the Order to Cash process."
    }
  ])

  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)

  const bottomRef = useRef(null)
  const fgRef = useRef(null)

  const [highlightNodes, setHighlightNodes] = useState(new Set())
  const [chatCollapsed, setChatCollapsed] = useState(false)
  const [showGranular, setShowGranular] = useState(true)
  const [analytics, setAnalytics] = useState(null)

  const nodeColorMap = {
    Orders: "#0ea5e9",
    Deliveries: "#10b981",
    Invoices: "#ec4899",
    Payments: "#8b5cf6",
    Customers: "#f59e0b",
    Journal: "#f43f5e"
  }

  const getNodeColor = (n) => nodeColorMap[n.type] || "#94a3b8"

  useEffect(() => {
    axios.get(`${API}/graph`).then((r) => setGraph(r.data))

    axios.get(`${API}/analytics`).then((r) =>
      setAnalytics(r.data)
    )
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth"
    })
  }, [messages])

  const send = async () => {
    if (!input.trim() || loading) return

    const q = input

    setInput("")
    setLoading(true)

    setMessages((m) => [
      ...m,
      { role: "user", text: q }
    ])

    try {
      const r = await axios.post(`${API}/query`, {
        question: q
      })

      setMessages((m) => [
        ...m,
        {
          role: "ai",
          text: r.data.answer
        }
      ])

      const h_nodes = r.data.highlight_nodes || []

      if (h_nodes.length > 0) {
        setHighlightNodes(new Set(h_nodes))

        const targetNode = graph.nodes.find((n) =>
          h_nodes.includes(n.id)
        )

        if (targetNode && fgRef.current) {
          const distance = 100

          const distRatio =
            1 +
            distance /
              Math.hypot(
                targetNode.x,
                targetNode.y,
                targetNode.z
              )

          fgRef.current.cameraPosition(
            {
              x: targetNode.x * distRatio,
              y: targetNode.y * distRatio,
              z: targetNode.z * distRatio
            },
            targetNode,
            1000
          )
        }
      } else {
        setHighlightNodes(new Set())
      }

      if (r.data.data && r.data.data.length > 0) {
        setPopupData({
          title:
            h_nodes.length > 0
              ? "Target Record Details"
              : "Query Results",
          rows: r.data.data
        })
      } else {
        setPopupData(null)
      }
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "ai",
          text: "Server error. Is backend running?"
        }
      ])
    }

    setLoading(false)
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        width: "100%",
        background:
          "linear-gradient(180deg,#020617 0%,#020617 100%)",
        overflowX: "hidden",
        padding: "20px",
        boxSizing: "border-box"
      }}
    >
      {/* TOP NAV */}

      <div className="top-nav">
        <div
          style={{
            display: "flex",
            alignItems: "center"
          }}
        >
          <div className="nav-icon">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <rect
                x="3"
                y="3"
                width="18"
                height="18"
                rx="2"
              />
            </svg>
          </div>

          <span className="nav-divider">|</span>

          <span>Mapping</span>

          <span className="nav-divider">/</span>

          <span className="nav-current">
            Order to Cash
          </span>
        </div>

        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            gap: "12px"
          }}
        >
          <button
            className="cmd-btn cmd-light"
            onClick={() =>
              setChatCollapsed(!chatCollapsed)
            }
          >
            {chatCollapsed ? "Maximize" : "Minimize"}
          </button>

          <button
            className="cmd-btn cmd-dark"
            onClick={() =>
              setShowGranular(!showGranular)
            }
          >
            {showGranular
              ? "Hide Overlay"
              : "Show Overlay"}
          </button>
        </div>
      </div>

      {/* KPI SECTION */}

      {analytics && (
        <div
          style={{
            display: "flex",
            gap: "16px",
            width: "100%",
            overflowX: "auto",
            paddingBottom: "10px",
            marginTop: "20px"
          }}
        >
          <DashboardCard
            title="Orders"
            value={analytics.total_orders}
            color="#0ea5e9"
          />

          <DashboardCard
            title="Customers"
            value={analytics.total_customers}
            color="#f59e0b"
          />

          <DashboardCard
            title="Invoices"
            value={analytics.total_invoices}
            color="#ec4899"
          />

          <DashboardCard
            title="Payments"
            value={analytics.total_payments}
            color="#8b5cf6"
          />

          <DashboardCard
            title="Revenue"
            value={`$${analytics.total_revenue}`}
            color="#10b981"
          />
        </div>
      )}

      {/* MAIN WORKSPACE */}

      <div
        className="workspace-wrapper"
        style={{
          marginTop: "20px",
          width: "100%",
          height: "75vh",
          display: "flex",
          borderRadius: "24px",
          overflow: "hidden",
          border:
            "1px solid rgba(255,255,255,0.08)",
          background: "rgba(15,23,42,0.55)",
          backdropFilter: "blur(20px)"
        }}
      >
        {/* GRAPH PANEL */}

        <div
          className="graph-panel"
          style={{
            flex: 1,
            position: "relative"
          }}
        >
          <ForceGraph3D
            ref={fgRef}
            graphData={graph}
            backgroundColor="rgba(0,0,0,0)"
            nodeLabel={null}
            onEngineStop={() =>
              fgRef.current?.zoomToFit(800, 80)
            }
            nodeThreeObject={(node) => {
              const color = getNodeColor(node)

              const isHighlighted =
                highlightNodes.has(node.id)

              const isFaded =
                highlightNodes.size > 0 &&
                !isHighlighted

              const group = new THREE.Group()

              const geometry =
                new THREE.SphereGeometry(
                  isHighlighted ? 7 : 5,
                  32,
                  32
                )

              const material =
                new THREE.MeshStandardMaterial({
                  color: isHighlighted
                    ? "#ffffff"
                    : color,
                  emissive: isHighlighted
                    ? color
                    : "#000000",
                  emissiveIntensity:
                    isHighlighted ? 0.8 : 0,
                  transparent: true,
                  opacity: isFaded ? 0.15 : 1
                })

              const sphere = new THREE.Mesh(
                geometry,
                material
              )

              group.add(sphere)

              if (!isFaded && showGranular) {
                const sprite = new SpriteText(
                  node.type || ""
                )

                sprite.color = isHighlighted
                  ? "#ffffff"
                  : "#94a3b8"

                sprite.textHeight = 5

                sprite.position.set(0, 12, 0)

                group.add(sprite)
              }

              return group
            }}
            linkWidth={(link) => {
              if (highlightNodes.size > 0) {
                const srcId =
                  typeof link.source === "object"
                    ? link.source.id
                    : link.source

                const tgtId =
                  typeof link.target === "object"
                    ? link.target.id
                    : link.target

                return highlightNodes.has(srcId) ||
                  highlightNodes.has(tgtId)
                  ? 1.5
                  : 0.2
              }

              return 0.5
            }}
            linkColor={(link) => {
              if (highlightNodes.size > 0) {
                const srcId =
                  typeof link.source === "object"
                    ? link.source.id
                    : link.source

                const tgtId =
                  typeof link.target === "object"
                    ? link.target.id
                    : link.target

                return highlightNodes.has(srcId) ||
                  highlightNodes.has(tgtId)
                  ? "rgba(56,189,248,0.6)"
                  : "rgba(255,255,255,0.03)"
              }

              return "rgba(148,163,184,0.15)"
            }}
          />

          {/* POPUP */}

          {popupData && (
            <div
              style={{
                position: "absolute",
                top: 20,
                left: 20,
                background:
                  "rgba(15,23,42,0.9)",
                padding: "18px",
                borderRadius: "14px",
                maxWidth: "420px",
                maxHeight: "70vh",
                overflow: "auto",
                zIndex: 20
              }}
            >
              <div
                style={{
                  fontWeight: "700",
                  marginBottom: "12px",
                  color: "#fff"
                }}
              >
                {popupData.title}
              </div>

              {popupData.rows.map((row, idx) => (
                <div key={idx}>
                  {Object.entries(row)
                    .slice(0, 10)
                    .map(([k, v]) => (
                      <div
                        key={k}
                        style={{
                          marginBottom: "8px",
                          fontSize: "12px"
                        }}
                      >
                        <span
                          style={{
                            color: "#94a3b8"
                          }}
                        >
                          {k}:
                        </span>{" "}
                        <span
                          style={{
                            color: "#fff"
                          }}
                        >
                          {String(v)}
                        </span>
                      </div>
                    ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* CHAT PANEL */}

        {!chatCollapsed && (
          <div
            className="chat-panel"
            style={{
              width: "380px",
              borderLeft:
                "1px solid rgba(255,255,255,0.08)",
              display: "flex",
              flexDirection: "column",
              background:
                "rgba(15,23,42,0.65)"
            }}
          >
            <div
              style={{
                padding: "20px",
                borderBottom:
                  "1px solid rgba(255,255,255,0.08)"
              }}
            >
              <div
                style={{
                  color: "#fff",
                  fontSize: "24px",
                  fontWeight: "700"
                }}
              >
                Chat with Graph
              </div>

              <div
                style={{
                  color: "#94a3b8",
                  marginTop: "4px"
                }}
              >
                ORDER TO CASH
              </div>
            </div>

            <div
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "20px"
              }}
            >
              {messages.map((m, i) => (
                <div
                  key={i}
                  style={{
                    marginBottom: "16px"
                  }}
                >
                  <div
                    style={{
                      background:
                        m.role === "user"
                          ? "#0ea5e9"
                          : "rgba(255,255,255,0.06)",
                      padding: "14px",
                      borderRadius: "14px",
                      color: "#fff"
                    }}
                  >
                    {m.text}
                  </div>
                </div>
              ))}

              <div ref={bottomRef} />
            </div>

            <div
              style={{
                padding: "20px",
                borderTop:
                  "1px solid rgba(255,255,255,0.08)"
              }}
            >
              <textarea
                value={input}
                onChange={(e) =>
                  setInput(e.target.value)
                }
                placeholder="Analyze anything"
                style={{
                  width: "100%",
                  minHeight: "90px",
                  borderRadius: "14px",
                  border:
                    "1px solid rgba(255,255,255,0.1)",
                  background:
                    "rgba(255,255,255,0.04)",
                  color: "#fff",
                  padding: "14px",
                  resize: "none",
                  outline: "none"
                }}
              />

              <button
                onClick={send}
                style={{
                  marginTop: "12px",
                  width: "100%",
                  padding: "14px",
                  borderRadius: "12px",
                  border: "none",
                  background: "#0ea5e9",
                  color: "#fff",
                  fontWeight: "700",
                  cursor: "pointer"
                }}
              >
                {loading ? "Thinking..." : "Send"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* FOOTER */}

      <div
        style={{
          marginTop: "24px",
          width: "100%",
          padding: "18px 24px",
          borderRadius: "18px",
          background: "rgba(15,23,42,0.65)",
          border:
            "1px solid rgba(255,255,255,0.08)",
          backdropFilter: "blur(20px)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px"
        }}
      >
        <div>
          <div
            style={{
              color: "#ffffff",
              fontSize: "15px",
              fontWeight: "700"
            }}
          >
            Dodge AI Analytics Platform
          </div>

          <div
            style={{
              color: "#94a3b8",
              fontSize: "13px",
              marginTop: "4px"
            }}
          >
            Intelligent Order-to-Cash Process
            Visualization
          </div>
        </div>

        <div
          style={{
            display: "flex",
            gap: "18px",
            alignItems: "center",
            flexWrap: "wrap"
          }}
        >
          <span
            style={{
              color: "#0ea5e9",
              fontSize: "13px",
              fontWeight: "600"
            }}
          >
            Real-time Graph Insights
          </span>

          <span
            style={{
              color: "#10b981",
              fontSize: "13px",
              fontWeight: "600"
            }}
          >
            AI Powered Analytics
          </span>

          <span
            style={{
              color: "#ec4899",
              fontSize: "13px",
              fontWeight: "600"
            }}
          >
            Interactive Visualization
          </span>
        </div>
      </div>
    </div>
  )
}

function DashboardCard({ title, value, color }) {
  return (
    <div
      style={{
        background: "rgba(15,23,42,0.75)",
        border: `1px solid ${color}55`,
        borderRadius: "16px",
        padding: "18px",
        minWidth: "220px",
        flex: "0 0 220px",
        backdropFilter: "blur(20px)",
        boxShadow: `0 0 20px ${color}22`
      }}
    >
      <div
        style={{
          color: "#94a3b8",
          fontSize: "13px",
          marginBottom: "10px",
          fontWeight: "600"
        }}
      >
        {title}
      </div>

      <div
        style={{
          color,
          fontSize: "28px",
          fontWeight: "800"
        }}
      >
        {value}
      </div>
    </div>
  )
}

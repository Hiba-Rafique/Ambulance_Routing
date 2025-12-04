"use client"

import type React from "react"
import { useEffect, useMemo, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { fetchDebugDijkstra, type DebugDijkstraResponse } from "@/lib/api"

interface DijkstraVisualizerProps {
  requestId: number
}

// Simple SVG padding around projected node coordinates
const PADDING = 80
const NODE_RADIUS = 18

export const DijkstraVisualizer: React.FC<DijkstraVisualizerProps> = ({ requestId }) => {
  const [data, setData] = useState<DebugDijkstraResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stepIndex, setStepIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)

  // Load debug data once for this request
  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const result = await fetchDebugDijkstra(requestId)
        if (!cancelled) {
          setData(result)
          setStepIndex(0)
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message || "Failed to load Dijkstra debug data")
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
      setIsPlaying(false)
    }
  }, [requestId])

  // Auto-play through steps
  useEffect(() => {
    if (!isPlaying || !data) return
    if (stepIndex >= data.steps.length - 1) {
      setIsPlaying(false)
      return
    }
    const id = setTimeout(() => {
      setStepIndex((i) => Math.min(i + 1, data.steps.length - 1))
    }, 900)
    return () => clearTimeout(id)
  }, [isPlaying, stepIndex, data])

  const step = data && data.steps.length > 0 ? data.steps[Math.min(stepIndex, data.steps.length - 1)] : null

  // Project nodes to SVG coordinates using a simple layered layout
  // based on the actual graph topology (levels from the source node),
  // rather than raw lat/lon. This keeps the structure faithful to the
  // real graph but spaces nodes/edges out more cleanly.
  const projected = useMemo(() => {
    if (!data || data.nodes.length === 0) {
      return { width: 900, height: 520, positions: {} as Record<number, { x: number; y: number }> }
    }

    const width = 900
    const height = 520

    // Build adjacency list from edges
    const adj: Record<number, number[]> = {}
    for (const e of data.edges) {
      if (!adj[e.from_node]) adj[e.from_node] = []
      if (!adj[e.to_node]) adj[e.to_node] = []
      adj[e.from_node].push(e.to_node)
      adj[e.to_node].push(e.from_node)
    }

    // BFS from source node to assign a "layer" (distance) to each node.
    const sourceId = data.source_node_id
    const layer: Record<number, number> = {}
    const queue: number[] = []

    if (sourceId != null) {
      layer[sourceId] = 0
      queue.push(sourceId)
      while (queue.length > 0) {
        const u = queue.shift() as number
        const neighbors = adj[u] || []
        for (const v of neighbors) {
          if (layer[v] === undefined) {
            layer[v] = layer[u] + 1
            queue.push(v)
          }
        }
      }
    }

    // Any nodes not reached in BFS get placed on the last layer.
    const maxAssignedLayer = Object.values(layer).reduce((m, v) => (v > m ? v : m), 0)
    const positions: Record<number, { x: number; y: number }> = {}
    const layers: Record<number, number[]> = {}

    for (const n of data.nodes as DebugDijkstraResponse["nodes"]) {
      const l = layer[n.id] !== undefined ? layer[n.id] : maxAssignedLayer + 1
      if (!layers[l]) layers[l] = []
      layers[l].push(n.id)
    }

    const layerIndices = Object.keys(layers)
      .map((k) => Number(k))
      .sort((a, b) => a - b)
    const layerCount = layerIndices.length || 1

    const usableWidth = width - 2 * PADDING
    const usableHeight = height - 2 * PADDING
    const stepX = layerCount > 1 ? usableWidth / (layerCount - 1) : 0

    for (let i = 0; i < layerIndices.length; i++) {
      const layerId = layerIndices[i]
      const nodeIds = layers[layerId].sort((a, b) => a - b)
      const count = nodeIds.length

      const stepY = count > 1 ? usableHeight / (count - 1) : 0
      const baseX = PADDING + i * stepX

      for (let j = 0; j < nodeIds.length; j++) {
        const id = nodeIds[j]
        const y = count === 1 ? height / 2 : PADDING + j * stepY
        positions[id] = { x: baseX, y }
      }
    }

    return { width, height, positions }
  }, [data])

  const handlePrev = () => {
    setStepIndex((i) => Math.max(0, i - 1))
    setIsPlaying(false)
  }

  const handleNext = () => {
    if (!data) return
    setStepIndex((i) => Math.min(i + 1, data.steps.length - 1))
    setIsPlaying(false)
  }

  const handleReset = () => {
    setStepIndex(0)
    setIsPlaying(false)
  }

  const handlePlayPause = () => {
    if (!data) return
    setIsPlaying((p) => !p)
  }

  const getNodeFill = (id: number): string => {
    if (!step) return "#d1d5db"
    if (data && data.shortest_path.includes(id)) return "#10b981" // final path – emerald green
    if (step.current === id) return "#1f2937" // current – dark blue-gray
    if (step.visited.includes(id)) return "#10b981" // visited – emerald green
    if (step.frontier.includes(id)) return "#fbbf24" // frontier – amber
    return "#d1d5db" // default – light gray
  }

  const getNodeStroke = (id: number): string => {
    if (!data) return "#ffffff"
    if (id === data.source_node_id) return "#10b981" // source – green
    if (id === data.destination_node_id) return "#f97316" // destination – orange
    return "#ffffff"
  }

  return (
    <Card className="p-6 md:p-8 space-y-6 bg-background border-border">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h3 className="font-semibold text-lg md:text-xl">Dijkstra Algorithm Pathfinding</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Real city graph · edge weights in minutes · emerald path = optimal route
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={handleReset} disabled={!data || loading}>
            Reset
          </Button>
          <Button size="sm" variant="outline" onClick={handlePrev} disabled={!data || stepIndex === 0 || loading}>
            ← Prev
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleNext}
            disabled={!data || stepIndex >= data.steps.length - 1 || loading}
          >
            Next →
          </Button>
          <Button
            size="sm"
            variant={isPlaying ? "default" : "outline"}
            onClick={handlePlayPause}
            disabled={!data || loading || data.steps.length <= 1}
          >
            {isPlaying ? "⏸ Pause" : "▶ Play"}
          </Button>
        </div>
      </div>

      {loading && <p className="text-sm text-muted-foreground animate-pulse">Loading Dijkstra visualization…</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {data && step && (
        <div className="space-y-6">
          <div className="w-full flex justify-center overflow-x-auto rounded-lg border border-border bg-gradient-to-br from-slate-50 to-slate-100">
            <svg
              width={projected.width}
              height={projected.height}
              className="bg-white"
              style={{
                filter: "drop-shadow(0 1px 2px rgba(0, 0, 0, 0.05))",
              }}
            >
              {/* Subtle grid background */}
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#f3f4f6" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width={projected.width} height={projected.height} fill="url(#grid)" opacity="0.5" />

              {/* edges */}
              {data.edges.map((e: DebugDijkstraResponse["edges"][number]) => {
                const from = projected.positions[e.from_node]
                const to = projected.positions[e.to_node]
                if (!from || !to) return null

                // Edge is on the final shortest path iff it connects
                // consecutive nodes in the shortest_path array.
                let isOnPath = false
                for (let i = 0; i < data.shortest_path.length - 1; i++) {
                  const a = data.shortest_path[i]
                  const b = data.shortest_path[i + 1]
                  if ((e.from_node === a && e.to_node === b) || (e.from_node === b && e.to_node === a)) {
                    isOnPath = true
                    break
                  }
                }

                // Edge currently being "tried" this step: incident to the
                // current node we are expanding.
                const isFromCurrent = step.current !== null && e.from_node === step.current
                const isToCurrent = step.current !== null && e.to_node === step.current
                const isCurrentEdge = isFromCurrent || isToCurrent

                // Edge whose both endpoints have already been visited can be
                // shown as dimmed, since Dijkstra has effectively finalized it.
                const bothVisited = step.visited.includes(e.from_node) && step.visited.includes(e.to_node)

                let stroke = "#bfdbfe"
                let strokeWidth = 2
                let strokeOpacity = 0.6
                let strokeDasharray: string | undefined

                if (bothVisited) {
                  stroke = "#e5e7eb"
                  strokeOpacity = 0.35
                  strokeWidth = 1.5
                }
                if (isCurrentEdge) {
                  stroke = "#3b82f6"
                  strokeWidth = 3.5
                  strokeOpacity = 0.9
                }

                // Roadblocks and traffic conditions override base styling so
                // they stand out clearly in red/orange.
                if (e.is_blocked) {
                  stroke = "#ef4444" // red for blocked roads
                  strokeWidth = 4
                  strokeOpacity = 0.95
                  strokeDasharray = "6 3"
                } else if (e.has_traffic) {
                  stroke = "#f97316" // orange for heavy traffic
                  strokeWidth = 3.5
                  strokeOpacity = 0.9
                }

                // Only highlight the final shortest path on the LAST step.
                const isFinalStep = data.steps && data.steps.length > 0 && stepIndex === data.steps.length - 1
                if (isOnPath && isFinalStep) {
                  stroke = "#10b981"
                  strokeWidth = 5
                  strokeOpacity = 1
                  strokeDasharray = undefined
                }

                const midX = (from.x + to.x) / 2
                const midY = (from.y + to.y) / 2 - 6

                return (
                  <g key={e.id}>
                    <defs>
                      <marker
                        id={`arrowhead-${e.id}`}
                        markerWidth="10"
                        markerHeight="10"
                        refX="9"
                        refY="3"
                        orient="auto"
                      >
                        <polygon points="0 0, 10 3, 0 6" fill={stroke} opacity={strokeOpacity} />
                      </marker>
                    </defs>
                    <line
                      x1={from.x}
                      y1={from.y}
                      x2={to.x}
                      y2={to.y}
                      stroke={stroke}
                      strokeWidth={strokeWidth}
                      strokeOpacity={strokeOpacity}
                      strokeDasharray={strokeDasharray}
                      markerEnd={`url(#arrowhead-${e.id})`}
                    />
                    {/* weight label with improved styling */}
                    <rect
                      x={midX - 14}
                      y={midY - 9}
                      width={28}
                      height={16}
                      rx={4}
                      ry={4}
                      fill={isOnPath ? "#d1fae5" : "#f9fafb"}
                      stroke={isOnPath ? "#10b981" : "#e5e7eb"}
                      strokeWidth={1}
                    />
                    <text
                      x={midX}
                      y={midY + 3}
                      fontSize="11"
                      fontWeight="600"
                      textAnchor="middle"
                      fill={isOnPath ? "#047857" : "#374151"}
                    >
                      {e.weight.toFixed(1)}
                    </text>
                  </g>
                )
              })}

              {/* nodes */}
              {data.nodes.map((n: DebugDijkstraResponse["nodes"][number]) => {
                const pos = projected.positions[n.id]
                if (!pos) return null
                const fill = getNodeFill(n.id)
                const stroke = getNodeStroke(n.id)

                return (
                  <g key={n.id}>
                    <defs>
                      <filter id={`shadow-${n.id}`}>
                        <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.15" />
                      </filter>
                    </defs>
                    {/* Node circle with improved appearance */}
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={NODE_RADIUS}
                      fill={fill}
                      stroke={stroke}
                      strokeWidth={2.5}
                      filter={`url(#shadow-${n.id})`}
                      style={{ transition: "all 0.2s ease" }}
                    />
                    {/* node id - bolder and more readable */}
                    <text x={pos.x} y={pos.y + 6} fontSize="13" fontWeight="700" textAnchor="middle" fill="#ffffff">
                      {n.id}
                    </text>
                    {/* role label with improved positioning */}
                    {data && n.id === data.source_node_id && (
                      <text x={pos.x} y={pos.y + 42} fontSize="11" fontWeight="600" textAnchor="middle" fill="#047857">
                        PATIENT
                      </text>
                    )}
                    {data && n.id === data.destination_node_id && (
                      <text x={pos.x} y={pos.y + 42} fontSize="11" fontWeight="600" textAnchor="middle" fill="#ea580c">
                        HOSPITAL
                      </text>
                    )}
                  </g>
                )
              })}
            </svg>
          </div>

          <div className="bg-slate-50 rounded-lg p-4 space-y-3 border border-slate-200">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Step Progress</p>
                <p className="text-base font-semibold text-foreground mt-1">
                  {stepIndex + 1} of {data.steps.length}
                  {step.current !== null && ` · Expanding node ${step.current}`}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Status</p>
                <p className="text-base font-semibold text-foreground mt-1">
                  {stepIndex === data.steps.length - 1 ? "✓ Complete" : "In Progress"}
                </p>
              </div>
            </div>

            <div className="border-t border-slate-200 pt-3 space-y-2">
              <p className="text-sm">
                <span className="font-semibold text-foreground">Optimal Path: </span>
                <span className="font-mono text-sm text-slate-700">
                  {data.shortest_path.length > 0 ? data.shortest_path.join(" → ") : "unreachable"}
                </span>
              </p>
              {data.shortest_path.length > 0 && (
                <p className="text-sm">
                  <span className="font-semibold text-foreground">Total Time: </span>
                  <span className="font-mono font-semibold text-emerald-700">
                    {(() => {
                      const lastStep = data.steps[data.steps.length - 1]
                      const d = lastStep.distances[data.destination_node_id]
                      return d !== undefined ? `${d.toFixed(2)} min` : "—"
                    })()}
                  </span>
                </p>
              )}
              {data.total_distance_km != null && (
                <p className="text-sm">
                  <span className="font-semibold text-foreground">Total Distance: </span>
                  <span className="font-mono font-semibold text-blue-700">{data.total_distance_km.toFixed(2)} km</span>
                </p>
              )}
            </div>

            {/* Legend */}
            <div className="border-t border-slate-200 pt-3">
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">Legend</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs text-slate-600">
                <div>● Dark gray = current node</div>
                <div>● Amber = frontier</div>
                <div>● Emerald = visited/path</div>
                <div>🔵 Blue edge = exploring</div>
                <div>🟢 Green outline = source</div>
                <div>🟠 Orange outline = dest</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}

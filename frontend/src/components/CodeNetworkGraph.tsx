import React, { useMemo, useState, useCallback, useRef } from 'react';

interface NetworkNode {
  id: string;
  data: { label: string };
  position: { x: number; y: number };
}

interface NetworkEdge {
  id: string;
  source: string;
  target: string;
}

interface NetworkGraphType {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

interface ProcessedNode extends NetworkNode {
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  nodeType: 'repository' | 'contributor';
  level: number;
  children?: string[];
}

interface NetworkGraphProps {
  data: NetworkGraphType;
  fullscreen?: boolean;
}

const NetworkGraph: React.FC<NetworkGraphProps> = ({ data, fullscreen = false }) => {
  const { nodes: rawNodes, edges: rawEdges } = data;
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; content: string } | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Process the real data for hierarchical org chart rendering
  const processedData = useMemo(() => {
    if (!rawNodes || !rawEdges) {
      return { nodes: [], edges: [], svgWidth: 1200, svgHeight: 800, edgeMap: new Map() };
    }

    const svgWidth = 1400;
    const svgHeight = 1000;
    const nodeWidth = 140;
    const nodeHeight = 50;

    // Separate repositories and contributors by ID prefix
    const repositories = rawNodes.filter(node => node.id.startsWith('repo-'));
    const contributors = rawNodes.filter(node => node.id.startsWith('contrib-'));
    
    console.log(`Found ${repositories.length} repositories and ${contributors.length} contributors`);
    
    // Create connection map
    const edgeMap = new Map<string, Set<string>>();
    rawEdges.forEach(edge => {
      if (!edgeMap.has(edge.source)) edgeMap.set(edge.source, new Set());
      if (!edgeMap.has(edge.target)) edgeMap.set(edge.target, new Set());
      edgeMap.get(edge.source)!.add(edge.target);
      edgeMap.get(edge.target)!.add(edge.source);
    });

    const processedNodes: ProcessedNode[] = [];
    
    // Level 0: Root/Organization header
    processedNodes.push({
      id: 'org-root',
      data: { label: 'Team' },
      position: { x: svgWidth / 2, y: 40 },
      x: svgWidth / 2 - nodeWidth / 2,
      y: 40,
      width: nodeWidth + 20,
      height: nodeHeight,
      color: '#6366f1',
      nodeType: 'repository' as const,
      level: 0
    });

    // Level 1: Repositories - spread them out properly
    const repoSpacing = Math.max(nodeWidth + 30, svgWidth / (repositories.length + 1));
    repositories.forEach((repo, index) => {
      const x = 50 + index * repoSpacing;
      processedNodes.push({
        ...repo,
        x: x,
        y: 140,
        width: nodeWidth,
        height: nodeHeight,
        color: '#3b82f6',
        nodeType: 'repository' as const,
        level: 1
      });
    });

    // Level 2: Contributors - arrange in a simple grid to avoid overlaps
    const contribCols = Math.ceil(Math.sqrt(contributors.length));
    const contribSpacing = Math.max(nodeWidth + 20, svgWidth / contribCols);
    const contribRowHeight = 80;
    
    contributors.forEach((contributor, index) => {
      const row = Math.floor(index / contribCols);
      const col = index % contribCols;
      const x = 50 + col * contribSpacing;
      const y = 260 + row * contribRowHeight;
      
      processedNodes.push({
        ...contributor,
        x: x,
        y: y,
        width: nodeWidth - 10,
        height: nodeHeight - 5,
        color: '#10b981',
        nodeType: 'contributor' as const,
        level: 2
      });
    });

    // Simplified edges - just connect repos to contributors
    const processedEdges = rawEdges
      .filter(edge => {
        const sourceNode = processedNodes.find(n => n.id === edge.source);
        const targetNode = processedNodes.find(n => n.id === edge.target);
        return sourceNode && targetNode;
      })
      .slice(0, 50) // Reduce edges for better performance
      .map(edge => {
        const sourceNode = processedNodes.find(n => n.id === edge.source)!;
        const targetNode = processedNodes.find(n => n.id === edge.target)!;
        return {
          ...edge,
          x1: sourceNode.x + sourceNode.width / 2,
          y1: sourceNode.y + sourceNode.height,
          x2: targetNode.x + targetNode.width / 2,
          y2: targetNode.y
        };
      });

    return { nodes: processedNodes, edges: processedEdges, svgWidth, svgHeight, edgeMap };
  }, [rawNodes, rawEdges]);

  // Zoom and pan handlers
  const handleZoomIn = useCallback(() => {
    setZoom(prev => Math.min(prev * 1.2, 3));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom(prev => Math.max(prev / 1.2, 0.3));
  }, []);

  const handleResetView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target === svgRef.current) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Simplified hover handlers for better performance
  const handleNodeMouseEnter = useCallback((event: React.MouseEvent, node: ProcessedNode) => {
    setHoveredNode(node.id);
    
    const svgRect = (event.currentTarget as SVGElement).closest('svg')?.getBoundingClientRect();
    if (svgRect) {
      setTooltip({
        x: event.clientX - svgRect.left + 10,
        y: event.clientY - svgRect.top - 10,
        content: `${node.nodeType === 'repository' ? '📁' : '👤'} ${node.data.label}`
      });
    }
  }, []);

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredNode(null);
    setTooltip(null);
  }, []);

  const handleNodeClick = useCallback((node: ProcessedNode) => {
    setSelectedNode(selectedNode === node.id ? null : node.id);
    console.log(`${node.nodeType} clicked:`, node.data.label);
  }, [selectedNode]);

  // Optimized styling functions - memoize to reduce calculations
  const getNodeStyle = useCallback((node: ProcessedNode) => {
    const isHovered = hoveredNode === node.id;
    const isSelected = selectedNode === node.id;
    
    return {
      fill: isSelected ? '#fbbf24' : node.color,
      stroke: isHovered || isSelected ? '#1f2937' : '#e5e7eb',
      strokeWidth: isHovered || isSelected ? '2' : '1',
      opacity: 1,
      filter: isHovered || isSelected ? 'drop-shadow(0 4px 8px rgba(0,0,0,0.2))' : 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))',
      cursor: 'pointer'
    };
  }, [hoveredNode, selectedNode]);

  const getEdgeStyle = useCallback((edge: any) => {
    const isConnected = hoveredNode && (edge.source === hoveredNode || edge.target === hoveredNode);
    
    return {
      stroke: isConnected ? '#475569' : '#d1d5db',
      strokeWidth: isConnected ? '2' : '1',
      opacity: isConnected ? 0.8 : 0.4
    };
  }, [hoveredNode]);

  return (
    <div 
      className="w-full border border-gray-200 rounded-lg overflow-hidden bg-white relative"
      style={{ height: fullscreen ? '100vh' : '90vh' }}
    >
      {/* Header with debug info and controls */}
      <div className="p-2 bg-gray-100 text-xs border-b flex justify-between items-center">
        <span>
          Debug: Raw data = {rawNodes?.length || 0} nodes, {rawEdges?.length || 0} edges | 
          Processed = {processedData.nodes.length} nodes, {processedData.edges.length} edges
        </span>
        {selectedNode && (
          <span className="text-blue-600 font-medium">
            Selected: {processedData.nodes.find(n => n.id === selectedNode)?.data.label}
          </span>
        )}
      </div>

      {/* Zoom Controls */}
      <div className="absolute top-16 right-4 z-10 flex flex-col space-y-2">
        <button
          onClick={handleZoomIn}
          className="w-8 h-8 bg-white border border-gray-300 rounded shadow hover:bg-gray-50 flex items-center justify-center text-sm font-bold"
          title="Zoom In"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          className="w-8 h-8 bg-white border border-gray-300 rounded shadow hover:bg-gray-50 flex items-center justify-center text-sm font-bold"
          title="Zoom Out"
        >
          −
        </button>
        <button
          onClick={handleResetView}
          className="w-8 h-8 bg-white border border-gray-300 rounded shadow hover:bg-gray-50 flex items-center justify-center text-xs"
          title="Reset View"
        >
          ⌂
        </button>
      </div>
      
      <div 
        className="w-full h-full overflow-hidden bg-gray-50"
        style={{ height: 'calc(100% - 32px)' }}
      >
        <svg 
          ref={svgRef}
          width="100%" 
          height="100%" 
          style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Grid background */}
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#f3f4f6" strokeWidth="1"/>
              </pattern>
            </defs>
            <rect width={processedData.svgWidth} height={processedData.svgHeight} fill="url(#grid)" />

            {/* Draw simplified connecting lines */}
            {processedData.edges.map((edge) => (
              <line
                key={edge.id}
                x1={edge.x1}
                y1={edge.y1}
                x2={edge.x2}
                y2={edge.y2}
                style={getEdgeStyle(edge)}
              />
            ))}
            
            {/* Draw org chart boxes */}
            {processedData.nodes.map((node) => (
              <g key={node.id}>
                {/* Node box */}
                <rect
                  x={node.x}
                  y={node.y}
                  width={node.width}
                  height={node.height}
                  rx="6"
                  style={getNodeStyle(node)}
                  onMouseEnter={(e) => handleNodeMouseEnter(e, node)}
                  onMouseLeave={handleNodeMouseLeave}
                  onClick={() => handleNodeClick(node)}
                />
                {/* Node text */}
                <text
                  x={node.x + node.width / 2}
                  y={node.y + node.height / 2 - 5}
                  textAnchor="middle"
                  fill="white"
                  fontSize="12"
                  fontWeight="600"
                  style={{ pointerEvents: 'none' }}
                >
                  {node.data.label.length > 18 
                    ? node.data.label.substring(0, 18) + '...' 
                    : node.data.label}
                </text>
                {/* Node type indicator */}
                <text
                  x={node.x + node.width / 2}
                  y={node.y + node.height / 2 + 10}
                  textAnchor="middle"
                  fill="rgba(255,255,255,0.8)"
                  fontSize="10"
                  style={{ pointerEvents: 'none' }}
                >
                  {node.nodeType === 'repository' ? 'Repository' : 'Contributor'}
                </text>
              </g>
            ))}

            {/* Tooltip */}
            {tooltip && (
              <g>
                <rect
                  x={tooltip.x}
                  y={tooltip.y - 30}
                  width={tooltip.content.length * 8 + 16}
                  height="35"
                  fill="rgba(0,0,0,0.9)"
                  rx="6"
                />
                <text
                  x={tooltip.x + 8}
                  y={tooltip.y - 10}
                  fill="white"
                  fontSize="12"
                  fontWeight="500"
                >
                  {tooltip.content}
                </text>
              </g>
            )}
          </g>
        </svg>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white border border-gray-200 rounded-lg p-3 shadow-lg text-xs">
        <div className="flex items-center space-x-4 mb-2">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-3 bg-indigo-500 rounded"></div>
            <span>Organization</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-3 bg-blue-500 rounded"></div>
            <span>Repository</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-3 bg-green-500 rounded"></div>
            <span>Contributor</span>
          </div>
        </div>
        <div className="text-gray-600 space-y-1">
          <div>• Drag to pan • Zoom with controls</div>
          <div>• Hover/click for interactions</div>
        </div>
      </div>
    </div>
  );
};

export default NetworkGraph; 
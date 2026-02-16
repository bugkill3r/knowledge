'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  ConnectionLineType,
  Panel,
  EdgeProps,
  getStraightPath,
  Handle,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { FileText, Code2, Table, Folder, X, Maximize2, Filter, Eye, EyeOff } from 'lucide-react';
import dagre from 'dagre';

interface KnowledgeGraphProps {
  collectionId?: string;
}

interface GraphData {
  nodes: Node[];
  edges: Edge[];
  stats: {
    total_nodes: number;
    total_edges: number;
    document_count: number;
    repository_count: number;
    spreadsheet_count: number;
    collection_count: number;
  };
}

// Custom node components
function DocumentNode({ data }: { data: any }) {
  return (
    <>
      <Handle type="target" position={Position.Top} />
      <div className="px-4 py-3 rounded-lg border-2 border-blue-500/50 bg-blue-500/10 backdrop-blur-sm min-w-[180px] max-w-[250px] hover:border-blue-500 transition-all cursor-pointer group">
        <div className="flex items-start gap-2">
          <FileText className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-foreground truncate group-hover:text-blue-400 transition-colors">
              {data.label}
            </div>
            {data.doc_type && (
              <div className="text-xs text-muted-foreground mt-1">
                {data.doc_type.toUpperCase()}
              </div>
            )}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </>
  );
}

function RepositoryNode({ data }: { data: any }) {
  return (
    <>
      <Handle type="target" position={Position.Top} />
      <div className="px-4 py-3 rounded-lg border-2 border-green-500/50 bg-green-500/10 backdrop-blur-sm min-w-[180px] max-w-[250px] hover:border-green-500 transition-all cursor-pointer group">
        <div className="flex items-start gap-2">
          <Code2 className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-foreground truncate group-hover:text-green-400 transition-colors">
              {data.label}
            </div>
            {data.language && (
              <div className="text-xs text-muted-foreground mt-1">
                {data.language}
              </div>
            )}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </>
  );
}

function SpreadsheetNode({ data }: { data: any }) {
  return (
    <>
      <Handle type="target" position={Position.Top} />
      <div className="px-3 py-2 rounded-lg border-2 border-yellow-500/50 bg-yellow-500/10 backdrop-blur-sm min-w-[140px] max-w-[200px] hover:border-yellow-500 transition-all cursor-pointer group">
        <div className="flex items-start gap-2">
          <Table className="w-3.5 h-3.5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-foreground truncate group-hover:text-yellow-400 transition-colors">
              {data.label}
            </div>
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </>
  );
}

function CollectionNode({ data }: { data: any }) {
  return (
    <>
      <Handle type="target" position={Position.Top} />
      <div 
        className="px-6 py-4 rounded-xl border-2 border-primary-blue bg-primary-blue/20 backdrop-blur-sm min-w-[200px] hover:border-primary-blue hover:bg-primary-blue/30 transition-all cursor-pointer shadow-lg"
        style={{ borderColor: data.color, backgroundColor: `${data.color}20` }}
      >
        <div className="flex items-center gap-3">
          <span className="text-3xl">{data.icon}</span>
          <div className="text-base font-bold text-foreground">
            {data.label}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </>
  );
}

// Custom edge for debugging
function CustomEdge({ id, sourceX, sourceY, targetX, targetY, style }: EdgeProps) {
  const [edgePath] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });

  return (
    <g>
      <path
        id={id}
        style={{ ...style, stroke: '#ff0000', strokeWidth: 5 }}
        className="react-flow__edge-path"
        d={edgePath}
      />
      <text>
        <textPath href={`#${id}`} style={{ fontSize: 12, fill: '#fff' }} startOffset="50%" textAnchor="middle">
          EDGE
        </textPath>
      </text>
    </g>
  );
}

  // Define node and edge types outside component to avoid recreation on every render
const nodeTypes = {
  document: DocumentNode,
  repository: RepositoryNode,
  spreadsheet: SpreadsheetNode,
  collection: CollectionNode,
};

const edgeTypes = {
  custom: CustomEdge,
};

// Layout algorithm using dagre
const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  
  const nodeWidth = 220;
  const nodeHeight = 80;
  
  dagreGraph.setGraph({ 
    rankdir: direction,
    nodesep: 200, // Even more spacing between nodes
    ranksep: 300, // Much more spacing between ranks
    marginx: 150,
    marginy: 150,
    ranker: 'longest-path', // Better layout algorithm
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { 
      width: node.type === 'collection' ? 250 : node.type === 'spreadsheet' ? 180 : nodeWidth, 
      height: node.type === 'collection' ? 100 : node.type === 'spreadsheet' ? 60 : nodeHeight 
    });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: direction === 'TB' ? Position.Top : Position.Left,
      sourcePosition: direction === 'TB' ? Position.Bottom : Position.Right,
      position: {
        x: nodeWithPosition.x - (node.type === 'collection' ? 125 : node.type === 'spreadsheet' ? 90 : nodeWidth / 2),
        y: nodeWithPosition.y - (node.type === 'collection' ? 50 : node.type === 'spreadsheet' ? 30 : nodeHeight / 2),
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

export default function KnowledgeGraph({ collectionId }: KnowledgeGraphProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Filters
  const [showDocs, setShowDocs] = useState(true);
  const [showCode, setShowCode] = useState(true);
  const [showSheets, setShowSheets] = useState(true);
  const [layoutDirection, setLayoutDirection] = useState<'TB' | 'LR'>('TB');

  const fetchGraph = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      
      const params = new URLSearchParams();
      if (collectionId) params.append('collection_id', collectionId);
      params.append('include_docs', showDocs.toString());
      params.append('include_code', showCode.toString());
      params.append('include_sheets', showSheets.toString());
      
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/graph/knowledge-graph?${params}`
      );
      
      if (!res.ok) throw new Error('Failed to fetch graph');
      
      const data: GraphData = await res.json();
      setGraphData(data);
      
      // Apply layout and style edges based on type
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        data.nodes,
        data.edges.map(edge => {
          // Style semantic relationships differently
          const isRelated = edge.type === 'related';
          const isSheet = edge.type === 'has_sheet';
          
          return {
            ...edge,
            type: 'smoothstep',
            animated: edge.animated || false,
            label: edge.label || '',
            labelStyle: { 
              fill: 'hsl(210 40% 98%)', 
              fontSize: 10,
              fontWeight: 600
            },
            labelBgStyle: { 
              fill: 'hsl(210 15% 8%)', 
              fillOpacity: 0.9 
            },
            labelBgPadding: [4, 8],
            labelBgBorderRadius: 4,
            style: { 
              stroke: isRelated 
                ? 'hsl(142 76% 45%)' // Green for semantic relationships
                : isSheet 
                  ? 'hsl(45 93% 50%)' // Yellow for sheets
                  : 'hsl(217 91% 60%)', // Blue for others
              strokeWidth: isRelated ? 2 : 1.5,
              strokeDasharray: isSheet ? '5,5' : undefined,
              opacity: isRelated ? 0.7 : 0.5 // More subtle
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              width: 15,
              height: 15,
              color: isRelated 
                ? 'hsl(142 76% 45%)'
                : isSheet 
                  ? 'hsl(45 93% 50%)'
                  : 'hsl(217 91% 60%)',
            },
          };
        }),
        layoutDirection
      );

      // Verify node IDs exist and deduplicate edges
      const nodeIds = new Set(layoutedNodes.map(n => n.id));
      const seenEdges = new Set<string>();
      const validEdges = layoutedEdges.filter(e => {
        const valid = nodeIds.has(e.source) && nodeIds.has(e.target);
        if (!valid) return false;
        
        // Deduplicate by checking both directions
        const edgeKey1 = `${e.source}-${e.target}`;
        const edgeKey2 = `${e.target}-${e.source}`;
        
        if (seenEdges.has(edgeKey1) || seenEdges.has(edgeKey2)) return false;
        
        seenEdges.add(edgeKey1);
        return true;
      });

      setNodes(layoutedNodes);
      setTimeout(() => setEdges(validEdges), 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load graph');
    } finally {
      setLoading(false);
    }
  }, [collectionId, showDocs, showCode, showSheets, layoutDirection, setNodes, setEdges]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    const data = node.data;
    
    if (data.entity_type === 'document' && data.source_url) {
      window.open(data.source_url, '_blank');
    } else if (data.entity_type === 'repository' && data.local_path) {
      // Could open in VS Code or show details
    } else if (data.entity_type === 'spreadsheet' && data.sheet_url) {
      window.open(data.sheet_url, '_blank');
    }
  }, []);

  const handleRelayout = () => {
    if (graphData) {
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        graphData.nodes,
        graphData.edges.map(edge => {
          const isRelated = edge.type === 'related';
          const isSheet = edge.type === 'has_sheet';
          
          return {
            ...edge,
            type: 'smoothstep',
            animated: edge.animated || false,
            label: edge.label || '',
            labelStyle: { 
              fill: 'hsl(210 40% 98%)', 
              fontSize: 10,
              fontWeight: 600
            },
            labelBgStyle: { 
              fill: 'hsl(210 15% 8%)', 
              fillOpacity: 0.9 
            },
            labelBgPadding: [4, 8],
            labelBgBorderRadius: 4,
            style: { 
              stroke: isRelated 
                ? 'hsl(142 76% 45%)'
                : isSheet 
                  ? 'hsl(45 93% 50%)'
                  : 'hsl(217 91% 60%)',
              strokeWidth: isRelated ? 2 : 1.5,
              strokeDasharray: isSheet ? '5,5' : undefined,
              opacity: isRelated ? 0.7 : 0.5
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              width: 15,
              height: 15,
              color: isRelated 
                ? 'hsl(142 76% 45%)'
                : isSheet 
                  ? 'hsl(45 93% 50%)'
                  : 'hsl(217 91% 60%)',
            },
          };
        }),
        layoutDirection
      );
      
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-muted-foreground shimmer-text">Building knowledge graph...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-red-400">{error}</div>
      </div>
    );
  }

  if (!graphData || graphData.stats.total_nodes === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📊</div>
          <div className="text-foreground text-lg font-medium mb-2">No data to visualize</div>
          <div className="text-muted-foreground text-sm">
            {collectionId ? 'This collection is empty' : 'Import some documents or code to see the graph'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        connectionLineType={ConnectionLineType.SmoothStep}
        fitView
        fitViewOptions={{ padding: 0.3, duration: 800 }}
        minZoom={0.05}
        maxZoom={3}
        defaultViewport={{ x: 0, y: 0, zoom: 0.5 }}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: false,
        }}
        elevateEdgesOnSelect={true}
        className="bg-background"
      >
        <Background color="hsl(210 15% 12%)" gap={16} />
        <Controls className="bg-card border border-border rounded-lg" />
        
        {/* Stats Panel */}
        <Panel position="top-left" className="bg-card/95 backdrop-blur-sm border border-border rounded-lg p-4 shadow-lg">
          <div className="text-sm font-semibold text-foreground mb-3">Knowledge Graph</div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between gap-4">
              <span className="text-muted-foreground">Nodes:</span>
              <span className="font-medium text-foreground">{graphData.stats.total_nodes}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-muted-foreground">Connections:</span>
              <span className="font-medium text-foreground">{graphData.stats.total_edges}</span>
            </div>
            <div className="h-px bg-border my-2" />
            <div className="flex items-center gap-2">
              <FileText className="w-3 h-3 text-blue-400" />
              <span className="text-muted-foreground">Documents:</span>
              <span className="font-medium text-foreground">{graphData.stats.document_count}</span>
            </div>
            <div className="flex items-center gap-2">
              <Code2 className="w-3 h-3 text-green-400" />
              <span className="text-muted-foreground">Repositories:</span>
              <span className="font-medium text-foreground">{graphData.stats.repository_count}</span>
            </div>
            <div className="flex items-center gap-2">
              <Table className="w-3 h-3 text-yellow-400" />
              <span className="text-muted-foreground">Sheets:</span>
              <span className="font-medium text-foreground">{graphData.stats.spreadsheet_count}</span>
            </div>
          </div>
          
          {/* Edge Legend */}
          <div className="mt-4 pt-3 border-t border-border">
            <div className="text-xs font-semibold text-foreground mb-2">Edge Types</div>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 bg-[hsl(142,76%,36%)]"></div>
                <span className="text-[10px] text-muted-foreground">Semantic</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 bg-[hsl(45,93%,47%)] border-dashed border-t border-[hsl(45,93%,47%)]"></div>
                <span className="text-[10px] text-muted-foreground">Has Sheet</span>
              </div>
            </div>
          </div>
        </Panel>

        {/* Filter Panel */}
        <Panel position="top-right" className="bg-card/95 backdrop-blur-sm border border-border rounded-lg p-4 shadow-lg">
          <div className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </div>
          <div className="space-y-2">
            <button
              onClick={() => setShowDocs(!showDocs)}
              className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-md text-xs transition-colors ${
                showDocs 
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' 
                  : 'bg-muted/50 text-muted-foreground border border-border'
              }`}
            >
              <span className="flex items-center gap-2">
                <FileText className="w-3 h-3" />
                Documents
              </span>
              {showDocs ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
            </button>
            
            <button
              onClick={() => setShowCode(!showCode)}
              className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-md text-xs transition-colors ${
                showCode 
                  ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                  : 'bg-muted/50 text-muted-foreground border border-border'
              }`}
            >
              <span className="flex items-center gap-2">
                <Code2 className="w-3 h-3" />
                Code
              </span>
              {showCode ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
            </button>
            
            <button
              onClick={() => setShowSheets(!showSheets)}
              className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-md text-xs transition-colors ${
                showSheets 
                  ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' 
                  : 'bg-muted/50 text-muted-foreground border border-border'
              }`}
            >
              <span className="flex items-center gap-2">
                <Table className="w-3 h-3" />
                Sheets
              </span>
              {showSheets ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
            </button>

            <div className="h-px bg-border my-2" />
            
            <button
              onClick={() => {
                setLayoutDirection(layoutDirection === 'TB' ? 'LR' : 'TB');
                setTimeout(handleRelayout, 100);
              }}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-xs bg-primary-blue/20 text-primary-blue border border-primary-blue/30 hover:bg-primary-blue/30 transition-colors"
            >
              <Maximize2 className="w-3 h-3" />
              {layoutDirection === 'TB' ? 'Horizontal' : 'Vertical'}
            </button>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}


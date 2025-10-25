import React, { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { ZoomIn, ZoomOut, Maximize2, Move } from 'lucide-react';

interface GraphNode {
  id: string;
  labels: string[];
  name?: string;
  english_name?: string;
  [key: string]: any;
}

interface GraphRelationship {
  id: string;
  type: string;
  start_node_id: string;
  end_node_id: string;
  [key: string]: any;
}

interface GraphVisualizationProps {
  nodes: GraphNode[];
  relationships: GraphRelationship[];
  height?: string;
  onNodeClick?: (node: GraphNode) => void;
}

interface NodePosition {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  nodes,
  relationships,
  height = '500px',
  onNodeClick
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const nodePositions = useRef<Map<string, NodePosition>>(new Map());
  const animationFrameId = useRef<number>();

  // Node type colors
  const getNodeColor = (labels: string[]) => {
    if (labels.includes('Ontology')) return '#3b82f6'; // blue
    if (labels.includes('Table')) return '#10b981'; // green
    if (labels.includes('Instance')) return '#f59e0b'; // amber
    if (labels.includes('Location')) return '#ef4444'; // red
    if (labels.includes('Concept')) return '#8b5cf6'; // purple
    return '#6b7280'; // gray
  };

  // Initialize node positions
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;

    // Clear existing positions
    nodePositions.current.clear();

    // Initialize positions in a circular layout
    nodes.forEach((node, index) => {
      const angle = (index / nodes.length) * Math.PI * 2;
      const radius = Math.min(width, height) * 0.3;
      nodePositions.current.set(node.id, {
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
        vx: 0,
        vy: 0
      });
    });
  }, [nodes]);

  // Force-directed layout simulation
  useEffect(() => {
    if (nodes.length === 0) return;

    const simulate = () => {
      const positions = nodePositions.current;
      const alpha = 0.1;
      const centerForce = 0.01;
      const repulsionForce = 5000;
      const attractionForce = 0.001;
      const damping = 0.9;

      // Apply forces
      nodes.forEach(node => {
        const pos = positions.get(node.id);
        if (!pos) return;

        // Center force
        const canvas = canvasRef.current;
        if (canvas) {
          pos.vx += (canvas.width / 2 - pos.x) * centerForce;
          pos.vy += (canvas.height / 2 - pos.y) * centerForce;
        }

        // Repulsion between nodes
        nodes.forEach(otherNode => {
          if (node.id === otherNode.id) return;
          const otherPos = positions.get(otherNode.id);
          if (!otherPos) return;

          const dx = pos.x - otherPos.x;
          const dy = pos.y - otherPos.y;
          const distance = Math.sqrt(dx * dx + dy * dy) || 1;
          
          const force = repulsionForce / (distance * distance);
          pos.vx += (dx / distance) * force * alpha;
          pos.vy += (dy / distance) * force * alpha;
        });
      });

      // Attraction along edges
      relationships.forEach(rel => {
        const startPos = positions.get(rel.start_node_id);
        const endPos = positions.get(rel.end_node_id);
        if (!startPos || !endPos) return;

        const dx = endPos.x - startPos.x;
        const dy = endPos.y - startPos.y;
        const distance = Math.sqrt(dx * dx + dy * dy) || 1;

        const force = distance * attractionForce;
        startPos.vx += dx * force;
        startPos.vy += dy * force;
        endPos.vx -= dx * force;
        endPos.vy -= dy * force;
      });

      // Update positions
      positions.forEach(pos => {
        pos.vx *= damping;
        pos.vy *= damping;
        pos.x += pos.vx;
        pos.y += pos.vy;
      });

      draw();
      animationFrameId.current = requestAnimationFrame(simulate);
    };

    // Run simulation for a limited time
    simulate();
    const timeout = setTimeout(() => {
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    }, 3000); // Stop after 3 seconds

    return () => {
      clearTimeout(timeout);
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, [nodes, relationships]);

  // Drawing function
  const draw = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Save context state
    ctx.save();
    
    // Apply transformations
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    // Draw relationships
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 1;
    relationships.forEach(rel => {
      const startPos = nodePositions.current.get(rel.start_node_id);
      const endPos = nodePositions.current.get(rel.end_node_id);
      if (!startPos || !endPos) return;

      ctx.beginPath();
      ctx.moveTo(startPos.x, startPos.y);
      ctx.lineTo(endPos.x, endPos.y);
      ctx.stroke();

      // Draw relationship type label
      const midX = (startPos.x + endPos.x) / 2;
      const midY = (startPos.y + endPos.y) / 2;
      ctx.fillStyle = '#64748b';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(rel.type, midX, midY - 5);
    });

    // Draw nodes
    nodes.forEach(node => {
      const pos = nodePositions.current.get(node.id);
      if (!pos) return;

      const isHovered = hoveredNode === node.id;
      const radius = isHovered ? 12 : 8;
      
      // Node circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = getNodeColor(node.labels);
      ctx.fill();
      ctx.strokeStyle = isHovered ? '#1e293b' : '#cbd5e1';
      ctx.lineWidth = isHovered ? 2 : 1;
      ctx.stroke();

      // Node label
      const label = node.name || node.english_name || node.id.split(':').pop() || '';
      ctx.fillStyle = '#1e293b';
      ctx.font = isHovered ? 'bold 12px sans-serif' : '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(label, pos.x, pos.y + radius + 15);
    });

    // Restore context state
    ctx.restore();
  };

  // Handle canvas resize
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;

      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
      draw();
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Mouse event handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - pan.x) / zoom;
    const y = (e.clientY - rect.top - pan.y) / zoom;

    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
      draw();
    } else {
      // Check for node hover
      let foundNode: string | null = null;
      nodes.forEach(node => {
        const pos = nodePositions.current.get(node.id);
        if (!pos) return;
        
        const distance = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2);
        if (distance < 15) {
          foundNode = node.id;
        }
      });
      
      if (foundNode !== hoveredNode) {
        setHoveredNode(foundNode);
        draw();
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
    setHoveredNode(null);
    draw();
  };

  const handleClick = (e: React.MouseEvent) => {
    if (!onNodeClick) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - pan.x) / zoom;
    const y = (e.clientY - rect.top - pan.y) / zoom;

    nodes.forEach(node => {
      const pos = nodePositions.current.get(node.id);
      if (!pos) return;
      
      const distance = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2);
      if (distance < 15) {
        onNodeClick(node);
      }
    });
  };

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev * 1.2, 3));
    draw();
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev / 1.2, 0.3));
    draw();
  };

  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    draw();
  };

  // Redraw when zoom or pan changes
  useEffect(() => {
    draw();
  }, [zoom, pan]);

  return (
    <div className="relative" style={{ height }}>
      <div 
        ref={containerRef}
        className="w-full h-full border rounded-lg bg-slate-50 dark:bg-slate-900 cursor-move"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
      >
        <canvas 
          ref={canvasRef}
          className="w-full h-full"
        />
      </div>
      
      {/* Controls */}
      <div className="absolute top-2 right-2 flex gap-1">
        <Button size="icon" variant="secondary" onClick={handleZoomIn}>
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button size="icon" variant="secondary" onClick={handleZoomOut}>
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button size="icon" variant="secondary" onClick={handleReset}>
          <Maximize2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Legend */}
      <div className="absolute bottom-2 left-2 bg-white dark:bg-slate-800 p-2 rounded-lg shadow-sm">
        <div className="text-xs font-medium mb-1">Node Types</div>
        <div className="flex flex-wrap gap-2">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span className="text-xs">Ontology</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-xs">Table</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-amber-500"></div>
            <span className="text-xs">Instance</span>
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="absolute top-2 left-2 text-xs text-muted-foreground">
        <Move className="inline h-3 w-3 mr-1" />
        Drag to pan • Click nodes for details
      </div>
    </div>
  );
};

export default GraphVisualization;
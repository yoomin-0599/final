import React, { useEffect, useRef } from 'react';
import { Paper, Typography } from '@mui/material';
import type { NetworkData } from '../api/newsApi';

interface KeywordNetworkProps {
  data: NetworkData;
}

export const KeywordNetwork: React.FC<KeywordNetworkProps> = ({ data }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !data.nodes.length) return;

    // Simple D3-like network visualization using canvas
    const container = containerRef.current;
    const canvas = document.createElement('canvas');
    const width = container.offsetWidth;
    const height = 500;
    canvas.width = width;
    canvas.height = height;
    container.innerHTML = '';
    container.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Simple force-directed layout
    const nodes = data.nodes.map((node) => ({
      ...node,
      x: Math.random() * width,
      y: Math.random() * height,
      vx: 0,
      vy: 0,
    }));

    const simulation = () => {
      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Draw edges
      ctx.strokeStyle = '#ddd';
      ctx.lineWidth = 1;
      data.edges.forEach(edge => {
        const source = nodes.find(n => n.id === edge.from);
        const target = nodes.find(n => n.id === edge.to);
        if (source && target) {
          ctx.beginPath();
          ctx.moveTo(source.x, source.y);
          ctx.lineTo(target.x, target.y);
          ctx.stroke();
        }
      });

      // Draw nodes
      nodes.forEach((node: any) => {
        const radius = Math.sqrt(node.value) * 3;
        
        // Node circle
        ctx.fillStyle = '#1976d2';
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
        ctx.fill();

        // Node label
        ctx.fillStyle = '#333';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y - radius - 5);
      });
    };

    simulation();

    // Simple interaction
    canvas.addEventListener('mousemove', (e) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Find nearest node
      let nearestNode: any = null;
      let minDist = Infinity;
      nodes.forEach((node: any) => {
        const dist = Math.sqrt(Math.pow(node.x - x, 2) + Math.pow(node.y - y, 2));
        if (dist < minDist && dist < Math.sqrt(node.value) * 3) {
          minDist = dist;
          nearestNode = node;
        }
      });

      if (nearestNode) {
        canvas.style.cursor = 'pointer';
        canvas.title = `${nearestNode.label} (${nearestNode.value})`;
      } else {
        canvas.style.cursor = 'default';
        canvas.title = '';
      }
    });

  }, [data]);

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        키워드 네트워크
      </Typography>
      <div ref={containerRef} style={{ minHeight: 500 }} />
    </Paper>
  );
};
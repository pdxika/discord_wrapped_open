import React, { useState, useEffect, useRef, useMemo } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import { api } from '../api';

interface VectorPoint {
    id: string;
    x: number;
    y: number;
    z: number;
    content: string;
    author: string;
    timestamp: string;
    date: string;
    channel_id?: string;
    message_id?: string;
}

const COLORS = [
    '#ef4444', '#f97316', '#f59e0b', '#84cc16', '#10b981',
    '#06b6d4', '#3b82f6', '#6366f1', '#8b5cf6', '#d946ef', '#f43f5e'
];

const VectorSpace: React.FC = () => {
    const [data, setData] = useState<{ nodes: VectorPoint[], links: any[] }>({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [authors, setAuthors] = useState<string[]>([]);
    const fgRef = useRef<any>();

    useEffect(() => {
        api.getVectorSpace()
            .then(res => {
                if (res.error) {
                    setError(res.error);
                } else {
                    const points = res.points || [];
                    setData({ nodes: points, links: [] });

                    // Extract unique authors for coloring
                    const uniqueAuthors = Array.from(new Set(points.map((p: VectorPoint) => p.author))).sort();
                    setAuthors(uniqueAuthors as string[]);
                }
                setLoading(false);
            })
            .catch(() => {
                setError("Failed to load galaxy data.");
                setLoading(false);
            });
    }, []);

    useEffect(() => {
        // Zoom out initially to see clusters
        if (fgRef.current) {
            fgRef.current.d3Force('charge').strength(-100); // Spread out more?
            fgRef.current.cameraPosition({ z: 400 }); // Zoom out
        }
    }, [data]);

    const colorMap = useMemo(() => {
        const map: Record<string, string> = {};
        authors.forEach((author, i) => {
            map[author] = COLORS[i % COLORS.length];
        });
        return map;
    }, [authors]);

    if (loading) return <div className="flex justify-center items-center h-96 text-blue-400 animate-pulse">Loading the Galaxy...</div>;
    if (error) return <div className="flex justify-center items-center h-96 text-red-400">{error}</div>;

    return (
        <div className="bg-gray-900 rounded-xl h-[800px] flex flex-col relative overflow-hidden">
            {/* Header / Controls Overlay */}
            <div className="absolute top-4 left-4 z-10 bg-gray-900/80 backdrop-blur p-4 rounded-lg border border-gray-700 max-w-sm pointer-events-none select-none">
                <h2 className="text-2xl font-bold text-white mb-1">Conversation Galaxy</h2>
                <p className="text-gray-400 text-xs mb-2">
                    Every star is a message. Colors represent authors.
                </p>
                <div className="text-xs text-gray-500 space-y-1">
                    <div>🖱️ Left Click + Drag to Rotate</div>
                    <div>🖱️ Right Click + Drag to Pan</div>
                    <div>🖱️ Scroll to Zoom</div>
                    <div>✨ Click a star to read the message</div>
                    <div className="mt-2 pt-2 border-t border-gray-700">
                        <strong className="text-gray-300">Axes:</strong> Semantic Dimensions
                        <div className="text-[10px] text-gray-500">
                            (Abstract representations of meaning)
                        </div>
                    </div>
                </div>
            </div>

            {/* Legend Overlay */}
            <div className="absolute bottom-4 right-4 z-10 bg-gray-900/80 backdrop-blur p-4 rounded-lg border border-gray-700 max-h-60 overflow-y-auto pointer-events-auto">
                <h3 className="text-xs font-bold text-gray-400 mb-2 uppercase">Authors</h3>
                <div className="space-y-1">
                    {authors.map(author => (
                        <div key={author} className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: colorMap[author] }} />
                            <span className="text-xs text-gray-300">{author}</span>
                        </div>
                    ))}
                </div>
            </div>

            <div className="flex-1 w-full h-full cursor-move">
                <ForceGraph3D
                    ref={fgRef}
                    graphData={data}
                    nodeLabel="content"
                    nodeColor={(node: any) => colorMap[node.author] || '#999'}
                    nodeRelSize={6}
                    nodeVal={1}
                    linkOpacity={0.2}
                    backgroundColor="#000000"
                    controlType="orbit"
                    showNavInfo={false}
                    onNodeClick={(node: any) => {
                        // Focus on node
                        const distance = 40;
                        const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);

                        fgRef.current.cameraPosition(
                            { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }, // new position
                            node, // lookAt ({ x, y, z })
                            3000  // ms transition duration
                        );

                        // Open Discord Link
                        // Since we might not have them in 'node', we'll just show the alert for now but formatted better
                        // Wait, user asked to link to discord convo. 
                        // I need to check if 'node' has message_id, channel_id, guild_id.
                        // The VectorPoint interface has 'id' which might be message_id.
                        // I'll try to construct a link if possible, otherwise fallback to alert.

                        // Ideally: `https://discord.com/channels/${guildId}/${channelId}/${messageId}`

                        // For now, let's just show the alert as requested but maybe add a "Open" button? 
                        // Actually, window.open is better if we had the link.
                        // Let's stick to the alert for now as I don't have the IDs in the frontend data yet.

                        setTimeout(() => {
                            const guildId = import.meta.env.VITE_GUILD_ID || ''; // Set in .env
                            const channelId = node.channel_id;
                            const messageId = node.message_id || node.id;

                            if (channelId && messageId) {
                                const link = `https://discord.com/channels/${guildId}/${channelId}/${messageId}`;
                                if (window.confirm(`${node.author} (${node.date}):\n\n${node.content}\n\nOpen in Discord?`)) {
                                    window.open(link, '_blank');
                                }
                            } else {
                                alert(`${node.author} (${node.date}):\n\n${node.content}\n\n(Link unavailable: Missing channel ID)`);
                            }
                        }, 100);
                    }}
                />
            </div>
        </div>
    );
};

export default VectorSpace;

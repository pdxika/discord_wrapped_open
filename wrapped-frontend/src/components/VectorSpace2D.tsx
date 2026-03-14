import React, { useState, useEffect, useMemo } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
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
}

const COLORS = [
    '#ef4444', '#f97316', '#f59e0b', '#84cc16', '#10b981',
    '#06b6d4', '#3b82f6', '#6366f1', '#8b5cf6', '#d946ef', '#f43f5e'
];

const VectorSpace2D: React.FC = () => {
    const [data, setData] = useState<VectorPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [authors, setAuthors] = useState<string[]>([]);

    useEffect(() => {
        api.getVectorSpace()
            .then(res => {
                if (res.error) {
                    setError(res.error);
                } else {
                    const points = res.points || [];
                    setData(points);

                    // Extract unique authors for coloring
                    const uniqueAuthors = Array.from(new Set(points.map((p: VectorPoint) => p.author))).sort();
                    setAuthors(uniqueAuthors as string[]);
                }
                setLoading(false);
            })
            .catch(() => {
                setError("Failed to load vector data.");
                setLoading(false);
            });
    }, []);

    const colorMap = useMemo(() => {
        const map: Record<string, string> = {};
        authors.forEach((author, i) => {
            map[author] = COLORS[i % COLORS.length];
        });
        return map;
    }, [authors]);

    if (loading) return <div className="flex justify-center items-center h-96 text-blue-400 animate-pulse">Loading vectors...</div>;
    if (error) return <div className="flex justify-center items-center h-96 text-red-400">{error}</div>;

    return (
        <div className="bg-gray-900 rounded-xl p-6 h-[800px] flex flex-col">
            <div className="mb-6 flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold text-white mb-2">What's our vector, victor?</h2>
                    <p className="text-gray-400">
                        A flattened 2D projection of conversation clusters.
                    </p>
                </div>
                <div className="text-right text-sm text-gray-500">
                    <strong className="text-gray-400">Axes:</strong> Semantic Dimensions
                    <div className="text-xs">(Abstract representations of meaning)</div>
                </div>
            </div>

            <div className="flex-1 w-full min-h-0 relative">
                {/* Legend Overlay */}
                <div className="absolute top-0 right-0 z-10 bg-gray-800/80 backdrop-blur p-4 rounded-lg border border-gray-700 max-h-60 overflow-y-auto">
                    <h3 className="text-xs font-bold text-gray-400 mb-2 uppercase">Authors</h3>
                    <div className="space-y-1">
                        {authors.map(author => (
                            <div key={author} className="flex items-center gap-2 text-xs text-gray-300">
                                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: colorMap[author] }}></span>
                                {author}
                            </div>
                        ))}
                    </div>
                </div>

                <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                        <XAxis type="number" dataKey="x" name="X" hide />
                        <YAxis type="number" dataKey="y" name="Y" hide />
                        <Tooltip
                            cursor={{ strokeDasharray: '3 3' }}
                            content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                    const data = payload[0].payload;
                                    return (
                                        <div className="bg-gray-800 border border-gray-700 p-3 rounded shadow-xl max-w-xs z-50">
                                            <div className="font-bold mb-1" style={{ color: colorMap[data.author] }}>
                                                {data.author}
                                            </div>
                                            <div className="text-xs text-gray-500 mb-2">{data.date}</div>
                                            <div className="text-sm text-gray-300 line-clamp-4">
                                                {data.content}
                                            </div>
                                        </div>
                                    );
                                }
                                return null;
                            }}
                        />
                        <Scatter name="Messages" data={data} fill="#8884d8">
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={colorMap[entry.author] || '#fff'} />
                            ))}
                        </Scatter>
                    </ScatterChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default VectorSpace2D;

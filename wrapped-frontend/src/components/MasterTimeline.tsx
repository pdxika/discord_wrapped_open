import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Users, ExternalLink } from 'lucide-react';

// TODO: Replace with actual Server ID
// const GUILD_ID = "YOUR_SERVER_ID";

interface TimelineEvent {
    id: string;
    date: string;
    title: string;
    preview: string;
    participants: string[];
    type: 'event' | 'stat';
    channel_name?: string;
    is_inside_joke?: boolean;
    deep_link?: {
        channel_id: string;
        message_id: string;
    };
}

// Helper for ordinal dates (1st, 2nd, 3rd)
const getOrdinal = (n: number) => {
    const s = ["th", "st", "nd", "rd"];
    const v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

interface MasterTimelineProps {
    searchQuery?: string;
}

const MasterTimeline: React.FC<MasterTimelineProps> = ({ searchQuery = '' }) => {
    const [events, setEvents] = useState<TimelineEvent[]>([]);
    const [guildId, setGuildId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [expandedMonths, setExpandedMonths] = useState<Set<string>>(new Set());
    const [expandedId, setExpandedId] = useState<string | null>(null);

    useEffect(() => {
        api.getMasterTimeline().then(res => {
            setEvents(res.timeline);
            setGuildId(res.guild_id);
            setLoading(false);
        });
    }, []);

    // Filter events based on search query
    const filteredEvents = events.filter(event => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return (
            event.title.toLowerCase().includes(query) ||
            event.preview.toLowerCase().includes(query) ||
            event.participants.some(p => p.toLowerCase().includes(query)) ||
            (event.channel_name && event.channel_name.toLowerCase().includes(query))
        );
    });

    // Group by Month
    const groupedEvents = filteredEvents.reduce((acc, event) => {
        const date = new Date(event.date);
        const monthKey = date.toLocaleString('default', { month: 'long', year: 'numeric' });
        if (!acc[monthKey]) acc[monthKey] = [];
        acc[monthKey].push(event);
        return acc;
    }, {} as Record<string, TimelineEvent[]>);

    // Auto-expand months if searching
    useEffect(() => {
        if (searchQuery) {
            const allMonths = Object.keys(groupedEvents);
            const newExpanded = new Set(allMonths);
            setExpandedMonths(newExpanded);
        } else {
            setExpandedMonths(new Set()); // Collapse all if no search query
        }
    }, [searchQuery, events]); // Re-run when query or events change

    const toggleMonth = (monthKey: string) => {
        setExpandedMonths(prev => {
            const newSet = new Set(prev);
            if (newSet.has(monthKey)) {
                newSet.delete(monthKey);
            } else {
                newSet.add(monthKey);
            }
            return newSet;
        });
    };

    if (loading) return <div className="text-center p-8 animate-pulse text-blue-400">Loading history...</div>;

    const monthKeys = Object.keys(groupedEvents);

    const scrollToMonth = (monthKey: string) => {
        const element = document.getElementById(`month-${monthKey}`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
        }
    };

    return (
        <div className="flex bg-gray-900 min-h-screen text-white relative overflow-hidden">
            {/* Background Ambience */}
            <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-blue-900/10 rounded-full blur-[100px] pointer-events-none" />

            {/* Sticky Sidebar */}
            <nav className="hidden md:flex flex-col gap-2 p-8 fixed left-0 top-20 h-[80vh] overflow-y-auto z-50 w-32 no-scrollbar">
                {monthKeys.map(month => (
                    <button
                        key={month}
                        onClick={() => scrollToMonth(month)}
                        className={`text-left text-xs font-bold transition-colors py-1 uppercase tracking-wider ${expandedMonths.has(month) ? 'text-blue-400' : 'text-gray-500 hover:text-blue-300'}`}
                    >
                        {month.split(' ')[0]}
                    </button>
                ))}
            </nav>

            <div className="flex-1 p-8 md:pl-40 relative z-10">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="max-w-4xl mx-auto"
                >
                    <header className="text-center mb-16">
                        <h2 className="text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400">
                            Dischronology
                        </h2>
                        <p className="text-gray-400 text-lg">
                            Nov 2024 — Nov 2025
                        </p>
                    </header>

                    <div className="space-y-24 pb-24">
                        {monthKeys.map(month => (
                            <div key={month} id={`month-${month}`} className="relative">
                                {/* Month Header */}
                                <div className="sticky top-4 z-20 mb-8 flex items-center gap-4">
                                    <span className="bg-gray-900/80 backdrop-blur px-4 py-1 rounded-full text-blue-400 font-bold border border-blue-900/50">
                                        {month}
                                    </span>
                                    <button
                                        onClick={() => toggleMonth(month)}
                                        className="text-gray-500 hover:text-white text-xs uppercase tracking-widest"
                                    >
                                        {expandedMonths.has(month) ? 'Collapse' : 'Expand'}
                                    </button>
                                </div>

                                {/* Events in this month */}
                                <AnimatePresence>
                                    {expandedMonths.has(month) && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: 'auto', opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            className="relative border-l-2 border-gray-800 ml-4 space-y-8 overflow-hidden"
                                        >
                                            {groupedEvents[month].map((event, index) => {
                                                const date = new Date(event.date);
                                                const isExpanded = expandedId === event.id;
                                                const isInsideJoke = event.is_inside_joke;

                                                return (
                                                    <motion.div
                                                        key={event.id}
                                                        initial={{ opacity: 0, x: -20 }}
                                                        whileInView={{ opacity: 1, x: 0 }}
                                                        viewport={{ once: true, margin: "-50px" }}
                                                        transition={{ duration: 0.4, delay: index * 0.05 }}
                                                        className="pl-8 relative"
                                                    >
                                                        {/* Dot */}
                                                        <div className={`absolute left-[-5px] top-6 w-3 h-3 rounded-full border-2 transition-colors ${isInsideJoke ? 'bg-yellow-500 border-yellow-300' : 'bg-gray-600 border-gray-900 group-hover:bg-blue-500'}`} />

                                                        <motion.div
                                                            layout
                                                            onClick={() => setExpandedId(isExpanded ? null : event.id)}
                                                            className={`backdrop-blur-sm border rounded-xl p-6 cursor-pointer transition-all 
                                                                ${isInsideJoke
                                                                    ? 'bg-yellow-900/20 border-yellow-500/50 hover:bg-yellow-900/30'
                                                                    : 'bg-gray-800/40 border-gray-700/50 hover:bg-gray-800/60'}
                                                                ${isExpanded ? (isInsideJoke ? 'ring-1 ring-yellow-500/50' : 'ring-1 ring-blue-500/50 bg-gray-800/80') : ''}
                                                            `}
                                                        >
                                                            <div className="flex items-center justify-between mb-2">
                                                                <div className="flex items-center gap-3">
                                                                    <span className={`text-sm font-mono w-12 text-right ${isInsideJoke ? 'text-yellow-500 font-bold' : 'text-gray-500'}`}>
                                                                        {getOrdinal(date.getDate())}
                                                                    </span>
                                                                    <div>
                                                                        <h3 className={`text-lg font-bold ${isInsideJoke ? 'text-yellow-200' : 'text-white'}`}>
                                                                            {event.title}
                                                                            {isInsideJoke && <span className="ml-2 text-xs bg-yellow-500/20 text-yellow-300 px-2 py-0.5 rounded-full border border-yellow-500/30">INSIDE JOKE</span>}
                                                                        </h3>
                                                                        {event.channel_name && (
                                                                            <div className="text-xs text-blue-400 font-mono">#{event.channel_name}</div>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                                <MessageSquare size={14} className="text-gray-600" />
                                                            </div>

                                                            <p className="text-gray-400 text-sm line-clamp-2 italic font-serif mt-2">
                                                                "{event.preview}"
                                                            </p>

                                                            <AnimatePresence>
                                                                {isExpanded && (
                                                                    <motion.div
                                                                        initial={{ height: 0, opacity: 0 }}
                                                                        animate={{ height: 'auto', opacity: 1 }}
                                                                        exit={{ height: 0, opacity: 0 }}
                                                                        className="overflow-hidden mt-4 pt-4 border-t border-gray-700/50"
                                                                    >
                                                                        <div className="flex items-center gap-2 mb-3 text-xs text-blue-300 uppercase tracking-wider">
                                                                            <Users size={12} />
                                                                            <span>Top Participants</span>
                                                                        </div>
                                                                        <div className="flex flex-wrap gap-2 mb-6">
                                                                            {event.participants.map(p => (
                                                                                <span key={p} className="bg-blue-900/20 text-blue-200 px-2 py-1 rounded text-xs border border-blue-900/30">
                                                                                    {p}
                                                                                </span>
                                                                            ))}
                                                                        </div>

                                                                        {event.deep_link && (
                                                                            <a
                                                                                href={`https://discord.com/channels/${guildId || 'UNKNOWN'}/${event.deep_link.channel_id}/${event.deep_link.message_id}`}
                                                                                target="_blank"
                                                                                rel="noopener noreferrer"
                                                                                className="inline-flex items-center gap-2 bg-[#5865F2] hover:bg-[#4752C4] text-white px-4 py-2 rounded-lg text-sm font-bold transition-colors"
                                                                                onClick={(e) => e.stopPropagation()}
                                                                            >
                                                                                <ExternalLink size={14} />
                                                                                View in Discord
                                                                            </a>
                                                                        )}
                                                                    </motion.div>
                                                                )}
                                                            </AnimatePresence>
                                                        </motion.div>
                                                    </motion.div>
                                                );
                                            })}
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>
                        ))}
                    </div>
                </motion.div>
            </div>
        </div>
    );
};

export default MasterTimeline;

import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, MessageSquare, Clock, Award, Zap, Flame, Star, Quote } from 'lucide-react';
import { api } from '../api';
import { THEME } from './Dashboard';

const UserPage: React.FC = () => {
    const { username } = useParams<{ username: string }>();
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Use constant theme
    const theme = THEME;

    useEffect(() => {
        if (username) {
            api.getUserStats(username)
                .then(res => {
                    if (res.error) {
                        setError(res.error);
                    } else {
                        setData(res);
                    }
                    setLoading(false);
                })
                .catch(() => {
                    setError("Failed to load user data.");
                    setLoading(false);
                });
        }
    }, [username]);

    if (loading) return <div className={`min-h-screen ${theme.bg} ${theme.text} flex items-center justify-center`}>Loading profile...</div>;
    if (error || !data || !data.stats) return <div className={`min-h-screen ${theme.bg} ${theme.text} flex items-center justify-center`}>{error || "User not found"}</div>;

    const { stats: userStats, roast, persona, partner_message } = data;
    const { stats, relationships, best_moment } = userStats;

    return (
        <div className={`min-h-screen ${theme.bg} ${theme.text} p-8`}>
            <Link to="/" className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-8 transition-colors">
                <ArrowLeft size={20} /> Back to Dashboard
            </Link>

            <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Header Profile Card */}
                <div className={`p-8 rounded-3xl border ${theme.border} shadow-2xl relative overflow-hidden bg-gradient-to-br ${theme.gradient}`}>
                    <div className="absolute top-0 right-0 p-32 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

                    <div className="flex flex-col md:flex-row items-start gap-8 relative z-10">
                        <div className={`w-32 h-32 rounded-full flex items-center justify-center text-5xl font-bold shadow-lg ${theme.card} border ${theme.border} shrink-0`}>
                            {username?.charAt(0).toUpperCase()}
                        </div>

                        <div className="flex-1 w-full">
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                                <div>
                                    <h1 className="text-5xl font-bold mb-2">{username}</h1>
                                    <div className="text-2xl text-purple-400 font-serif italic">
                                        {persona?.role || "Server Member"}
                                    </div>
                                </div>
                                <span className={`px-4 py-2 rounded-full text-lg font-mono border ${theme.border} ${theme.accent} bg-black/40 self-start md:self-center`}>
                                    Rank #{stats.rank}
                                </span>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                                <div className={`bg-black/30 p-6 rounded-xl border-l-4 border-purple-500 italic opacity-90`}>
                                    <div className="text-xs uppercase tracking-widest text-purple-400 mb-2 font-bold">The Roast</div>
                                    "{roast}"
                                </div>

                                {persona?.description && (
                                    <div className={`bg-black/30 p-6 rounded-xl border-l-4 border-blue-500 opacity-90`}>
                                        <div className="text-xs uppercase tracking-widest text-blue-400 mb-2 font-bold">The Vibe</div>
                                        {persona.description}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                    {/* Left Column: Stats & Traits */}
                    <div className="space-y-6 lg:col-span-2">

                        {/* Key Stats Grid */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div className={`${theme.card} p-6 rounded-2xl border ${theme.border} hover:border-blue-500/50 transition-colors`}>
                                <div className="flex items-center gap-3 mb-2 text-blue-400">
                                    <MessageSquare size={20} />
                                    <h3 className="font-bold uppercase tracking-wider text-xs">Volume</h3>
                                </div>
                                <div className="text-3xl font-bold">{stats.messages_sent.toLocaleString()}</div>
                                <div className="text-sm opacity-60 mt-1">Messages Sent</div>
                            </div>

                            <div className={`${theme.card} p-6 rounded-2xl border ${theme.border} hover:border-yellow-500/50 transition-colors`}>
                                <div className="flex items-center gap-3 mb-2 text-yellow-400">
                                    <Flame size={20} />
                                    <h3 className="font-bold uppercase tracking-wider text-xs">Karma</h3>
                                </div>
                                <div className="text-3xl font-bold">{stats.reactions_received.toLocaleString()}</div>
                                <div className="text-sm opacity-60 mt-1">Reactions Received</div>
                            </div>

                            <div className={`${theme.card} p-6 rounded-2xl border ${theme.border} hover:border-green-500/50 transition-colors`}>
                                <div className="flex items-center gap-3 mb-2 text-green-400">
                                    <Clock size={20} />
                                    <h3 className="font-bold uppercase tracking-wider text-xs">Prime Time</h3>
                                </div>
                                <div className="text-2xl font-bold">{stats.most_active_weekday}s</div>
                                <div className="text-sm opacity-60">at {stats.most_active_hour}:00</div>
                            </div>
                        </div>

                        {/* Signature Traits */}
                        {persona?.signature_traits && (
                            <div className={`${theme.card} p-8 rounded-2xl border ${theme.border}`}>
                                <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                                    <Star className="text-yellow-400" /> Signature Traits
                                </h3>
                                <ul className="space-y-4">
                                    {persona.signature_traits.map((trait: string, i: number) => (
                                        <li key={i} className="flex gap-3 items-start">
                                            <span className="text-purple-400 mt-1">✦</span>
                                            <span className="text-gray-300 leading-relaxed">{trait}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Best Moment */}
                        {best_moment && (
                            <div className={`${theme.card} p-8 rounded-2xl border ${theme.border} relative overflow-hidden`}>
                                <div className="absolute top-0 right-0 p-24 bg-yellow-500/5 rounded-full blur-3xl pointer-events-none" />
                                <h3 className="text-xl font-bold mb-6 flex items-center gap-2 relative z-10">
                                    <Award className="text-yellow-400" /> Best Moment of 2025
                                </h3>
                                <div className="bg-black/40 p-6 rounded-xl border border-gray-700 relative z-10">
                                    <div className="text-xl italic text-gray-200 mb-4 font-serif">"{best_moment.content}"</div>
                                    <div className="flex justify-between items-end">
                                        <div className="text-sm text-gray-500">
                                            {new Date(best_moment.timestamp).toLocaleDateString(undefined, { dateStyle: 'long' })}
                                        </div>
                                        <div className="flex gap-2">
                                            {best_moment.reaction_types?.map((emoji: string, i: number) => (
                                                <span key={i} className="text-xl">{emoji}</span>
                                            ))}
                                            <span className="text-sm font-bold text-yellow-500 self-center ml-2">
                                                +{best_moment.reactions} reactions
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right Column: Vibe, Vocab, Partner */}
                    <div className="space-y-6">

                        {/* Partner Message (Yearbook) */}
                        {partner_message && (
                            <div className="bg-white text-black p-8 rounded-2xl shadow-xl transform rotate-1 hover:rotate-0 transition-transform duration-300 relative">
                                <div className="absolute -top-3 -left-3 text-4xl transform -rotate-12">📌</div>
                                <h3 className="text-lg font-bold mb-4 uppercase tracking-widest text-gray-500 border-b-2 border-gray-200 pb-2">
                                    From Your Bestie
                                </h3>
                                <div className="font-handwriting text-xl leading-relaxed mb-6 font-serif">
                                    "{partner_message.message}"
                                </div>
                                <div className="flex justify-between items-center">
                                    <div className="font-bold text-lg">- {partner_message.from_display_name}</div>
                                    <div className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                                        {partner_message.conversation_count} convos together
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Vibe Check */}
                        <div className={`${theme.card} p-6 rounded-2xl border ${theme.border}`}>
                            <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                                <Zap className="text-purple-400" /> Vibe Check
                            </h3>
                            <div className="space-y-6">
                                <div>
                                    <div className="flex justify-between text-sm mb-2">
                                        <span className="opacity-60">Emoji Usage</span>
                                        <span className="font-bold">{Math.round(stats.emoji_rate * 100)}%</span>
                                    </div>
                                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                                        <div className="h-full bg-yellow-400" style={{ width: `${Math.min(stats.emoji_rate * 100, 100)}%` }} />
                                    </div>
                                </div>
                                <div>
                                    <div className="flex justify-between text-sm mb-2">
                                        <span className="opacity-60">Yelling (All Caps)</span>
                                        <span className="font-bold">{Math.round(stats.caps_rate * 100)}%</span>
                                    </div>
                                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                                        <div className="h-full bg-red-500" style={{ width: `${Math.min(stats.caps_rate * 100, 100)}%` }} />
                                    </div>
                                </div>
                                <div>
                                    <div className="flex justify-between text-sm mb-2">
                                        <span className="opacity-60">Curiosity (Questions)</span>
                                        <span className="font-bold">{Math.round(stats.question_rate * 100)}%</span>
                                    </div>
                                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                                        <div className="h-full bg-blue-500" style={{ width: `${Math.min(stats.question_rate * 100, 100)}%` }} />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Vocabulary */}
                        <div className={`${theme.card} p-6 rounded-2xl border ${theme.border}`}>
                            <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                                <Quote className="text-pink-400" /> Top Vocabulary
                            </h3>
                            <div className="flex flex-wrap gap-2">
                                {stats.vocabulary.slice(0, 20).map((word: string, i: number) => (
                                    <span
                                        key={word}
                                        className={`px-3 py-1 rounded-lg text-sm transition-colors cursor-default bg-black/30 ${theme.text} border border-gray-800 hover:border-gray-600`}
                                        style={{ opacity: Math.max(0.6, 1 - (i * 0.03)) }}
                                    >
                                        {word}
                                    </span>
                                ))}
                            </div>
                        </div>

                    </div>
                </div>

                {/* Besties */}
                {relationships?.mutual_bestie && (
                    <div className={`p-8 rounded-3xl border ${theme.border} text-center bg-gradient-to-r ${theme.gradient}`}>
                        <h3 className={`text-lg uppercase tracking-widest font-bold mb-2 ${theme.accent}`}>Certified Bestie</h3>
                        <div className={`text-4xl font-bold ${theme.text} mb-2`}>{relationships.mutual_bestie.display_name || relationships.mutual_bestie.username}</div>
                        <p className="opacity-60 text-sm">You two reply to each other more than anyone else.</p>
                    </div>
                )}

            </div>
        </div>
    );
};

export default UserPage;

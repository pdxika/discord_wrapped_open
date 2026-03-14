import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, GroupStatsResponse, LeaderboardEntry } from '../api';
import VectorSpace from './VectorSpace';
import VectorSpace2D from './VectorSpace2D';
import MasterTimeline from './MasterTimeline';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

// Theme Definitions - Simplified to just Cosmic
export const THEME = {
  name: 'Cosmic',
  bg: 'bg-black',
  text: 'text-white',
  card: 'bg-gray-900/50 backdrop-blur-sm',
  border: 'border-gray-800',
  accent: 'text-purple-400',
  gradient: 'from-purple-900/20 to-pink-900/20',
  button: 'bg-white text-black hover:bg-gray-200'
};

const Dashboard: React.FC = () => {
  const [data, setData] = useState<GroupStatsResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'stats' | 'timeline' | 'galaxy' | 'chat' | 'vectorized'>('stats');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Personal Wrapped Intake State
  const [isIntakeOpen, setIsIntakeOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState('');

  // Theme is now constant
  const theme = THEME;

  useEffect(() => {
    api.getGroupStats()
      .then(res => {
        setData(res);
        setLoading(false);
        // Default to first user in list if available
        if (res.leaderboards?.top_talkers?.length > 0) {
          setSelectedUser(res.leaderboards.top_talkers[0].username);
        }
      })
      .catch(err => {
        console.error("Failed to load dashboard data:", err);
        setError("Failed to load data.");
        setLoading(false);
      });
  }, []);

  // Chat state
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState<{ role: 'user' | 'assistant', content: string }[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  const handleChatSubmit = async (e: React.SyntheticEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput;
    setChatInput('');
    setChatHistory(prev => [...prev, { role: 'user', content: userMsg }]);
    setChatLoading(true);

    try {
      const data = await api.chatWithServer(userMsg, chatHistory);
      setChatHistory(prev => [...prev, { role: 'assistant', content: data.response || "Error: " + data.error }]);
    } catch (err: any) {
      console.error("Chat error:", err);
      setChatHistory(prev => [...prev, { role: 'assistant', content: `Sorry, I crashed. (${err.message || "Unknown error"})` }]);
    } finally {
      setChatLoading(false);
    }
  };

  // Timeline Disruption state
  const [disruptionData, setDisruptionData] = useState<any>(null);
  const [activeDisruptionUser, setActiveDisruptionUser] = useState<string | null>(null);


  const handleDisruptionToggle = async (username: string, displayName: string) => {
    if (activeDisruptionUser === username) {
      // Toggle OFF (Restore)
      setDisruptionData(null);
      setActiveDisruptionUser(null);
      return;
    }

    // Toggle ON (Disrupt)
    try {
      const res = await api.getTimelineDisruption(username);
      setDisruptionData({ ...res, username: displayName });
      setActiveDisruptionUser(username);
    } catch (err: any) {
      console.error("Disruption error:", err);
      alert(`Failed to disrupt timeline: ${err.message || "Unknown error"}`);
    }
  };


  if (loading) return <div className={`min-h-screen ${theme.bg} ${theme.text} flex items-center justify-center`}>Loading the cosmos...</div>;
  if (error) return <div className={`min-h-screen ${theme.bg} ${theme.text} flex items-center justify-center`}>{error}</div>;


  // Calculate displayed stats (either original or disrupted)
  const displayedTotalMessages = disruptionData && data?.server_stats
    ? data.server_stats.total_messages + disruptionData.diff.message_count_delta
    : data?.server_stats?.total_messages || 0;



  // Filtered Data for Stats Tab
  const filteredTopTalkers = data?.leaderboards?.top_talkers?.filter((u: LeaderboardEntry) =>
    u.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.username.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const filteredAwards = Object.entries(data?.awards || {}).filter(([key, award]: [string, any]) =>
    (award.display_name?.toLowerCase() || '').includes(searchQuery.toLowerCase()) ||
    key.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (award.description?.toLowerCase() || '').includes(searchQuery.toLowerCase())
  );

  return (
    <div className={`min-h-screen ${theme.bg} ${theme.text} font-sans selection:bg-purple-500/30`}>

      {/* Intake Modal */}
      {isIntakeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className={`${theme.card} border ${theme.border} p-8 rounded-3xl max-w-md w-full shadow-2xl relative overflow-hidden`}>
            <div className="absolute top-0 right-0 p-24 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

            <h2 className="text-2xl font-bold mb-2 relative z-10">Who are you?</h2>
            <p className="text-gray-400 mb-6 relative z-10">Select your name to unlock your personal 2025 Wrapped.</p>

            <div className="space-y-4 relative z-10">
              <select
                value={selectedUser}
                onChange={(e) => setSelectedUser(e.target.value)}
                className={`w-full p-4 rounded-xl bg-black/50 border ${theme.border} text-white focus:outline-none focus:border-purple-500 transition-colors appearance-none cursor-pointer`}
              >
                {data?.leaderboards?.top_talkers?.map((user: any) => (
                  <option key={user.username} value={user.username}>
                    {user.display_name}
                  </option>
                ))}
              </select>

              <div className="flex gap-3">
                <button
                  onClick={() => setIsIntakeOpen(false)}
                  className="flex-1 py-3 rounded-xl font-bold border border-gray-700 hover:bg-gray-800 transition-colors"
                >
                  Cancel
                </button>
                <Link
                  to={`/user/${selectedUser}`}
                  className={`flex-1 py-3 rounded-xl font-bold text-center ${theme.accent} text-white shadow-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2`}
                >
                  Reveal <span className="text-xl">✨</span>
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className={`sticky top-0 z-40 backdrop-blur-xl border-b ${theme.border} bg-black/50`}>
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl ${theme.accent} flex items-center justify-center shadow-lg shadow-purple-500/20`}>
              <span className="text-xl">✨</span>
            </div>
            <h1 className="text-xl font-bold tracking-tight">
              Discord<span className="text-purple-400">Wrapped</span>
              <span className="ml-2 text-xs bg-white/10 px-2 py-1 rounded-full text-gray-400 font-mono">2025</span>
            </h1>
          </div>

          <div className="flex items-center gap-4">
            {/* Personal Wrapped Button */}
            <button
              onClick={() => setIsIntakeOpen(true)}
              className={`hidden md:flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-sm border border-purple-500/50 hover:bg-purple-500/10 transition-colors text-purple-300`}
            >
              <span className="text-lg">🎁</span> See Your Personal Wrapped
            </button>

            <nav className="flex bg-gray-800/50 p-1 rounded-lg">
              {[
                { id: 'overview', label: 'Overview', icon: '📊' },
                { id: 'stats', label: 'Stats', icon: '📈' },
                { id: 'timeline', label: 'Timeline', icon: '🕰️' },
                { id: 'galaxy', label: 'Galaxy', icon: '🌌' },
                { id: 'vectorized', label: 'Vectorized', icon: '📐' },
                { id: 'chat', label: 'Oracle', icon: '🤖' },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 flex items-center gap-2 ${activeTab === tab.id
                    ? 'bg-gray-700 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
                    }`}
                >
                  <span>{tab.icon}</span>
                  <span className="hidden lg:inline">{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'stats' && (
          <div className="space-y-8 animate-in fade-in duration-500">

            {/* Hero Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className={`${theme.card} p-6 rounded-xl border ${theme.border} hover:border-blue-500/50 transition-colors`}>
                <div className={`text-sm ${theme.accent} font-bold uppercase tracking-wider mb-2`}>Total Messages</div>
                <div className={`text-4xl font-bold ${theme.text}`}>{displayedTotalMessages.toLocaleString()}</div>
                <div className="text-xs text-gray-500 mt-2">All Time</div>
              </div>

              <div className={`${theme.card} p-6 rounded-xl border ${theme.border} hover:border-purple-500/50 transition-colors`}>
                <div className={`text-sm ${theme.accent} font-bold uppercase tracking-wider mb-2`}>Active Members</div>
                <div className={`text-4xl font-bold ${theme.text}`}>{data?.server_stats?.active_members_count}</div>
                <div className="text-xs text-gray-500 mt-2">Posted this year</div>
              </div>

              <div className={`${theme.card} p-6 rounded-xl border ${theme.border} hover:border-pink-500/50 transition-colors`}>
                <div className={`text-sm ${theme.accent} font-bold uppercase tracking-wider mb-2`}>Busiest Day</div>
                <div className={`text-2xl font-bold ${theme.text}`}>{data?.server_stats?.busiest_day?.date}</div>
                <div className="text-xs text-gray-500 mt-2">{data?.server_stats?.busiest_day?.count} messages</div>
              </div>

              <div className={`${theme.card} p-6 rounded-xl border ${theme.border} hover:border-yellow-500/50 transition-colors`}>
                <div className={`text-sm ${theme.accent} font-bold uppercase tracking-wider mb-2`}>Loudest Hour</div>
                <div className={`text-4xl font-bold ${theme.text}`}>{data?.server_stats?.most_active_hour}:00</div>
                <div className="text-xs text-gray-500 mt-2">Most active time</div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

              {/* Top Talkers / Disruption Toggle */}
              <div className={`${theme.card} p-6 rounded-xl col-span-full lg:col-span-2 border ${theme.border}`}>
                <div className="mb-4">
                  <h3 className={`text-xl font-bold ${theme.text} opacity-80`}>It's a Wondiscordful Life 🎬</h3>
                  <p className="text-sm text-gray-400 mt-1">Click someone to remove them and see what our year would have been like without them.</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mb-6">
                  {filteredTopTalkers.slice(0, 15).map((user, index) => (
                    <div
                      key={user.username}
                      onClick={() => handleDisruptionToggle(user.username, user.display_name)}
                      className={`
                        flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all border
                        ${activeDisruptionUser === user.username
                          ? 'bg-red-900/40 border-red-500 ring-1 ring-red-500'
                          : `bg-black/20 border-transparent hover:bg-black/40 hover:border-gray-600`
                        }
                      `}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${index < 3 ? 'bg-yellow-500 text-black' : 'bg-gray-700 text-gray-300'}`}>
                          {index + 1}
                        </div>
                        <div className="font-bold truncate max-w-[100px]">{user.display_name}</div>
                      </div>
                      <div className={`text-xs font-mono ${activeDisruptionUser === user.username ? 'text-red-400 font-bold' : 'text-gray-400'}`}>
                        {user.count.toLocaleString()}
                        {activeDisruptionUser === user.username && <span className="ml-1">(-{user.count.toLocaleString()})</span>}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Disruption Impact Details (Moved Here) */}
                {disruptionData && (
                  <div className="bg-red-900/10 border border-red-900/50 p-6 rounded-xl animate-in slide-in-from-top-4 duration-500">
                    <h2 className="text-2xl font-bold text-red-400 mb-6 flex items-center gap-2 font-serif">
                      Without {disruptionData.username}...
                    </h2>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                      <div>
                        <h4 className="text-lg font-bold text-gray-300 mb-2">The Butterfly Effect</h4>
                        <div className="space-y-4">
                          <div>
                            <div className="text-4xl font-bold text-white mb-1">
                              {disruptionData.diff.lost_conversations_count}
                            </div>
                            <div className="text-sm text-gray-500">Lost Conversations</div>
                          </div>

                          {/* New Stats */}
                          <div className="grid grid-cols-2 gap-4">
                            <div className="bg-black/20 p-3 rounded">
                              <div className="text-xl font-bold text-yellow-400">
                                {disruptionData.diff.avg_reply_time_delta ? `+${disruptionData.diff.avg_reply_time_delta}m` : '+0m'}
                              </div>
                              <div className="text-xs text-gray-400">Slower Replies</div>
                            </div>
                            <div className="bg-black/20 p-3 rounded">
                              <div className="text-xl font-bold text-blue-400">
                                {disruptionData.diff.sentiment_shift || 'N/A'}
                              </div>
                              <div className="text-xs text-gray-400">Vibe Shift</div>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div>
                        <h4 className="text-lg font-bold text-gray-300 mb-2">Lost Topics</h4>
                        <div className="flex flex-wrap gap-2 mb-4">
                          {disruptionData.diff.lost_topics.map((topic: string) => (
                            <span key={topic} className="bg-red-900/30 text-red-200 px-2 py-1 rounded text-sm">
                              {topic}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div>
                        <div className="flex items-start gap-4 mb-4">
                          <div className="bg-red-900/20 p-3 rounded-full">
                            <span className="text-2xl">👻</span>
                          </div>
                          <div>
                            <h4 className="text-lg font-bold text-gray-300">Without them...</h4>
                            <p className="text-gray-400 text-sm italic">
                              "{disruptionData.diff.summary}"
                            </p>
                          </div>
                        </div>

                        <div className="border-l border-red-900/30 pl-8">
                          <h4 className="text-lg font-bold text-gray-300 mb-2">What would our server be like without them?</h4>
                          <div className="text-lg italic text-gray-300 font-serif leading-relaxed">
                            "{disruptionData.diff.commentary}"
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Top Reactors (Karma) */}
              <div className={`${theme.card} p-6 rounded-xl border ${theme.border}`}>
                <h3 className={`text-xl font-bold mb-1 ${theme.text} opacity-80`}>Reaction Magnets</h3>
                <p className="text-xs text-gray-500 mb-4">Users who received the most reactions</p>
                <div className="space-y-3">
                  {data?.leaderboards?.top_reactors_received
                    ?.filter(u => u.display_name.toLowerCase().includes(searchQuery.toLowerCase()))
                    .slice(0, 5).map((user: any, i: number) => (
                      <div key={i} className="flex justify-between items-center text-sm p-2 rounded hover:bg-gray-700/50 transition-colors group">
                        <div className="flex items-center gap-3">
                          <span className="text-gray-600 font-mono w-4">#{i + 1}</span>
                          <Link to={`/user/${user.username}`} className={`font-bold ${theme.text} hover:${theme.accent} transition-colors`}>
                            {user.display_name}
                          </Link>
                        </div>
                        <div className="text-yellow-500 font-mono">{user.count.toLocaleString()} <span className="text-xs opacity-50">reactions</span></div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Conversation Pairs */}
              <div className={`${theme.card} p-6 rounded-xl border ${theme.border}`}>
                <h3 className={`text-xl font-bold mb-4 ${theme.text} opacity-80`}>Dynamic Duos</h3>
                <div className="space-y-3">
                  {data?.leaderboards?.top_conversation_pairs?.slice(0, 5).map((pair: any, i: number) => (
                    <div key={i} className="flex justify-between items-center text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-blue-400 font-bold">{pair.person1}</span>
                        <span className="text-gray-600">↔</span>
                        <span className="text-purple-400 font-bold">{pair.person2}</span>
                      </div>
                      <div className="text-gray-500">{pair.count} replies</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Weekly Activity Line Chart */}
            <div className={`${theme.card} p-6 rounded-xl border ${theme.border} h-[400px]`}>
              <h3 className={`text-xl font-bold mb-4 ${theme.text} opacity-80`}>Weekly Chat Volume</h3>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data?.server_stats?.weekly_activity || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="week"
                      stroke="#9CA3AF"
                      tick={{ fontSize: 10 }}
                      tickFormatter={(value) => value.split('-W')[1]}
                      label={{ value: 'Week Number', position: 'insideBottom', offset: -5, fill: '#9CA3AF', fontSize: 12 }}
                    />
                    <YAxis stroke="#9CA3AF" tick={{ fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px', color: '#F3F4F6' }}
                      labelStyle={{ color: '#9CA3AF' }}
                    />
                    <Line
                      type="monotone"
                      dataKey="count"
                      stroke="#3B82F6"
                      strokeWidth={3}
                      dot={{ r: 4, fill: '#1F2937', strokeWidth: 2 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Disruption Impact Card */}
            {disruptionData && (
              <div className="bg-red-900/10 border border-red-900/50 p-8 rounded-2xl animate-in slide-in-from-top-4 duration-500">
                <h2 className="text-3xl font-bold text-red-400 mb-6 flex items-center gap-2 font-serif">
                  <span>🎬</span> It's a Wondiscordful Life: Without {disruptionData.username}
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                  <div>
                    <h4 className="text-lg font-bold text-gray-300 mb-2">The Butterfly Effect</h4>
                    <div className="space-y-4">
                      <div>
                        <div className="text-4xl font-bold text-white mb-1">
                          {disruptionData.diff.lost_conversations_count}
                        </div>
                        <div className="text-sm text-gray-500">Lost Conversations</div>
                      </div>

                      {/* New Stats */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-black/20 p-3 rounded">
                          <div className="text-xl font-bold text-yellow-400">
                            {disruptionData.diff.avg_reply_time_delta ? `+${disruptionData.diff.avg_reply_time_delta}m` : '+0m'}
                          </div>
                          <div className="text-xs text-gray-400">Slower Replies</div>
                        </div>
                        <div className="bg-black/20 p-3 rounded">
                          <div className="text-xl font-bold text-blue-400">
                            {disruptionData.diff.sentiment_shift || 'N/A'}
                          </div>
                          <div className="text-xs text-gray-400">Vibe Shift</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-lg font-bold text-gray-300 mb-2">Lost Topics</h4>
                    <div className="flex flex-wrap gap-2 mb-4">
                      {disruptionData.diff.lost_topics.map((topic: string) => (
                        <span key={topic} className="bg-red-900/30 text-red-200 px-2 py-1 rounded text-sm">
                          {topic}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <div className="flex items-start gap-4 mb-4">
                      <div className="bg-red-900/20 p-3 rounded-full">
                        <span className="text-2xl">👻</span>
                      </div>
                      <div>
                        <h4 className="text-lg font-bold text-gray-300">Without them...</h4>
                        <p className="text-gray-400 text-sm italic">
                          "{disruptionData.diff.summary}"
                        </p>
                      </div>
                    </div>

                    <div className="border-l border-red-900/30 pl-8">
                      <h4 className="text-lg font-bold text-gray-300 mb-2">What would our server be like without them?</h4>
                      <div className="text-lg italic text-gray-300 font-serif leading-relaxed">
                        "{disruptionData.diff.commentary}"
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Awards List */}
            <div className={`${theme.card} p-6 rounded-xl border ${theme.border}`}>
              <h3 className={`text-xl font-bold mb-6 ${theme.text} opacity-80`}>Awards</h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredAwards.map(([key, award]) => {
                  const emoji = award.emoji || '🏆';
                  return (
                    <div key={key} className={`p-4 rounded-lg flex justify-between items-center group border border-transparent hover:border-gray-600 transition-all bg-black/20`}>
                      <div>
                        <div className={`font-bold text-lg flex items-center gap-2 ${theme.text}`}>
                          <span>{emoji}</span>
                          <span>{award.title || key.replace(/_/g, ' ')}</span>
                        </div>
                        <div className="text-xs text-gray-500 mt-1 line-clamp-2 group-hover:line-clamp-none transition-all">
                          {award.description}
                        </div>
                      </div>
                      <div className="text-right pl-4">
                        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Winner</div>
                        <Link
                          to={`/user/${award.winner}`}
                          onClick={(e: React.MouseEvent) => e.stopPropagation()}
                          className={`font-bold text-xl ${theme.accent} hover:underline z-20 relative`}
                        >
                          {award.display_name || award.winner}
                        </Link>
                      </div>
                    </div>
                  );
                })}
                {filteredAwards.length === 0 && <div className="text-gray-500 italic col-span-full">No awards found matching "{searchQuery}"</div>}
              </div>
            </div>
          </div>
        )}

        {
          activeTab === 'timeline' && (
            <div className="w-full h-full">
              <MasterTimeline searchQuery={searchQuery} />
            </div>
          )
        }

        {
          activeTab === 'galaxy' && (
            <div className="w-full h-full">
              <VectorSpace />
            </div>
          )
        }

        {
          activeTab === 'vectorized' && (
            <div className="w-full h-full">
              <VectorSpace2D />
            </div>
          )
        }

        {
          activeTab === 'chat' && (
            <div className={`${theme.card} p-8 rounded-xl text-center h-[600px] flex flex-col border ${theme.border}`}>
              <h2 className={`text-2xl font-bold mb-4 ${theme.text}`}>Chat with the Server</h2>
              <p className="text-gray-400 mb-4">
                You are talking TO the server itself. Ask questions about the server history, inside jokes, or just chat with the digital soul of the community.
              </p>

              <div className="flex-1 bg-black/20 rounded-lg p-4 mb-4 overflow-y-auto text-left space-y-4">
                {chatHistory.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] p-3 rounded-lg ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-200'
                      }`}>
                      <div className="text-xs opacity-50 mb-1">{msg.role === 'user' ? 'You' : 'Server'}</div>
                      {msg.content}
                    </div>
                  </div>
                ))}
                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-700 text-gray-200 p-3 rounded-lg animate-pulse">
                      ServerBot is typing...
                    </div>
                  </div>
                )}
              </div>

              <div className="p-4 border-t border-gray-700 flex gap-2">
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleChatSubmit(e)}
                  placeholder={chatLoading ? "ServerBot is typing..." : "Ask about the server history..."}
                  disabled={chatLoading}
                  className="flex-1 bg-gray-800 text-white px-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
                <button
                  onClick={handleChatSubmit}
                  disabled={chatLoading}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-bold disabled:opacity-50 transition-colors"
                >
                  Send
                </button>
              </div>
            </div>
          )
        }
      </main>
    </div>
  );
};

export default Dashboard;

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5002/api';

export interface ServerStats {
    total_messages: number;
    unique_authors: number;
    date_range: {
        start: string;
        end: string;
        days: number;
    };
    active_days_count?: number;
    active_members_count: number;
    busiest_day: {
        date: string;
        count: number;
    };
    most_active_hour: number;
    peak_activity: {
        date: string;
        date_message_count: number;
        hour: number;
        hour_message_count: number;
        weekday: string;
        weekday_message_count: number;
    };
    activity_heatmap: number[][];
    weekly_activity: { week: string; count: number }[];
    volume_by_week: Record<string, number>;
    channels: Record<string, number>;
    total_reactions: number;
    top_reaction_emojis: { emoji: string; count: number }[];
}

export interface LeaderboardEntry {
    username: string;
    display_name: string;
    count: number;
}

export interface Award {
    winner: string;
    display_name: string;
    description: string;
    [key: string]: any;
}

export interface PersonalityRead {
    role: string;
    description: string;
    signature_traits: string[];
    contribution: string;
}

export interface LLMAnalysis {
    personality_reads: Record<string, PersonalityRead>;
    sentiment_awards: Record<string, any>;
}

export interface GroupStatsResponse {
    server_stats: ServerStats;
    leaderboards: {
        top_talkers: LeaderboardEntry[];
        top_reactors_received: LeaderboardEntry[];
        top_repliers: LeaderboardEntry[];
        most_replied_to: LeaderboardEntry[];
        top_conversation_pairs: { person1: string; person2: string; count: number }[];
    };
    awards: Record<string, Award>;
    llm_analysis?: LLMAnalysis;
}

export const api = {
    getHealth: async () => {
        const res = await fetch(`${API_BASE}/health`);
        return res.json();
    },

    getGroupStats: async (): Promise<GroupStatsResponse> => {
        const res = await fetch(`${API_BASE}/stats/group`);
        return res.json();
    },

    getUserStats: async (username: string) => {
        const res = await fetch(`${API_BASE}/user/${username}`);
        if (!res.ok) throw new Error('User not found');
        return res.json();
    },

    async getTimelineDisruption(username: string) {
        const res = await fetch(`${API_BASE}/timeline/disruption/${username}`);
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || "Failed to get timeline disruption");
        }
        return res.json();
    },

    async getMasterTimeline() {
        const res = await fetch(`${API_BASE}/timeline/master`);
        if (!res.ok) throw new Error("Failed to get master timeline");
        return res.json();
    },

    async getVectorSpace() {
        const res = await fetch(`${API_BASE}/vector_space`);
        if (!res.ok) {
            const err = await res.json();
            return { error: err.error || "Failed to get vector space" };
        }
        return res.json();
    },

    async getConfig() {
        const res = await fetch(`${API_BASE}/config`);
        return res.json();
    },

    async chatWithServer(message: string, history: { role: 'user' | 'assistant', content: string }[] = []) {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, history })
        });

        if (!res.ok) {
            const text = await res.text();
            try {
                return JSON.parse(text);
            } catch {
                throw new Error(`Server error ${res.status}: ${text.slice(0, 50)}...`);
            }
        }

        return res.json();
    }
};

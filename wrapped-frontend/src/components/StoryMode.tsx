import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { api, GroupStatsResponse } from '../api';

const StoryMode: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [data, setData] = useState<GroupStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [disruptionData, setDisruptionData] = useState<any>(null);

  useEffect(() => {
    api.getGroupStats().then(stats => {
      setData(stats);
      setLoading(false);

      if (stats.leaderboards.top_talkers.length > 0) {
        const topTalker = stats.leaderboards.top_talkers[0];
        api.getTimelineDisruption(topTalker.username)
          .then(res => setDisruptionData({ ...res, username: topTalker.display_name }))
          .catch(err => console.error("Failed to load disruption", err));
      }
    });
  }, []);

  if (loading || !data) {
    return <div className="flex items-center justify-center h-screen bg-black text-white">Loading your memories...</div>;
  }

  // Define slides dynamically based on data
  const getSlides = () => {
    const baseSlides = [
      // Intro
      <div key="intro" className="flex flex-col items-center justify-center h-full text-center p-8">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-6xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600"
        >
          Discord Wrapped 2025
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-2xl text-gray-300"
        >
          Your Year in Review
        </motion.p>
      </div>,

      // Volume Stats
      <div key="volume" className="flex flex-col items-center justify-center h-full text-center p-8">
        <h2 className="text-4xl font-bold mb-8">We (literally) couldn't stop talking</h2>
        <div className="text-8xl font-black text-blue-500 mb-4">
          {data.server_stats.total_messages.toLocaleString()}
        </div>
        <p className="text-xl text-gray-400 mb-12">Total messages sent this year</p>

        <div className="text-6xl font-bold text-purple-400 mb-4">
          {data.server_stats.active_days_count || 365}
        </div>
        <p className="text-xl text-gray-400">Active days in our server</p>
      </div>,

      // Peak Activity
      <div key="peak" className="flex flex-col items-center justify-center h-full text-center p-8">
        <h2 className="text-4xl font-bold mb-8">Our wildest day was...</h2>
        <div className="text-6xl font-bold text-yellow-400 mb-4">
          {new Date(data.server_stats.peak_activity.date).toLocaleDateString(undefined, { month: 'long', day: 'numeric' })}
        </div>
        <p className="text-2xl text-gray-300">
          {data.server_stats.peak_activity.date_message_count} messages in 24 hours
        </p>
      </div>,

      // Person Cards (Stats + Role)
      ...data.leaderboards.top_talkers.slice(0, 15).map((person) => {
        // Find their role (persona)
        const persona = data.llm_analysis?.personality_reads?.[person.username];
        const role = persona ? persona.role : 'Server Member';

        return (
          <div key={`person_${person.username}`} className="flex flex-col items-center justify-center h-full text-center p-8">
            <h2 className="text-5xl font-bold mb-4">{person.display_name}</h2>
            <div className="text-2xl text-purple-400 mb-8 font-serif italic">{role}</div>

            <div className="grid grid-cols-1 gap-6">
              <div className="bg-gray-900/50 p-6 rounded-xl border border-gray-800">
                <div className="text-6xl font-black text-blue-500 mb-2">
                  {person.count.toLocaleString()}
                </div>
                <div className="text-gray-400 uppercase tracking-widest text-sm">Messages Sent</div>
              </div>
            </div>
          </div>
        );
      }),

      // Outro
      <div key="outro" className="flex flex-col items-center justify-center h-full text-center p-8">
        <h2 className="text-4xl font-bold mb-8">But that's just the surface...</h2>
        <button
          onClick={(e) => {
            e.stopPropagation();
            navigate('/');
          }}
          className="px-8 py-4 bg-white text-black font-bold rounded-full hover:bg-gray-200 transition-colors relative z-50"
        >
          Enter Dashboard
        </button>
      </div>
    ];
    return baseSlides;
  };

  const slides = getSlides();

  const nextSlide = () => {
    if (step < slides.length - 1) {
      setStep(step + 1);
    }
  };

  const prevSlide = () => {
    if (step > 0) {
      setStep(step - 1);
    }
  };

  return (
    <div className="h-screen w-screen bg-black text-white overflow-hidden relative" onClick={nextSlide}>
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 100 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -100 }}
          transition={{ duration: 0.5 }}
          className="h-full w-full absolute top-0 left-0"
        >
          {slides[step]}
        </motion.div>
      </AnimatePresence>

      {/* Progress Bar */}
      <div className="absolute top-0 left-0 w-full h-2 flex gap-1 p-2">
        {slides.map((_, i) => (
          <div
            key={i}
            className={`h-full flex-1 rounded-full transition-colors ${i <= step ? 'bg-white' : 'bg-gray-800'}`}
          />
        ))}
      </div>

      {/* Navigation Hints */}
      <div className="absolute bottom-8 left-0 w-full text-center text-gray-500 text-sm pointer-events-none">
        Tap right to continue • Tap left to go back
      </div>

      {/* Invisible Click Zones */}
      <div className="absolute top-0 left-0 w-1/3 h-full cursor-w-resize z-10" onClick={(e) => { e.stopPropagation(); prevSlide(); }} />
      <div className="absolute top-0 right-0 w-2/3 h-full cursor-e-resize z-10" onClick={(e) => { e.stopPropagation(); nextSlide(); }} />
    </div>
  );
};

export default StoryMode;

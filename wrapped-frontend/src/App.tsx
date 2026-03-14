import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import StoryMode from './components/StoryMode';
import Dashboard from './components/Dashboard';
import UserPage from './components/UserPage';
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  return (
    <Router>
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/story" element={<StoryMode />} />
          <Route path="/dashboard" element={<Navigate to="/" replace />} />
          <Route path="/user/:username" element={<UserPage />} />
        </Routes>
      </ErrorBoundary>
    </Router>
  );
}

export default App;

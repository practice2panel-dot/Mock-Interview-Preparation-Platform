import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';
import InterviewForm from './mockInterview/InterviewForm';
import InterviewScreen from './mockInterview/InterviewScreen';
import SummaryScreen from './mockInterview/SummaryScreen';
import './MockInterview.css';

const MockInterview = () => {
  const readJson = (key, fallback) => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  };

  const [currentScreen, setCurrentScreen] = useState(() => localStorage.getItem('mockInterview.currentScreen') || 'form');
  const [sessionData, setSessionData] = useState(() => readJson('mockInterview.sessionData', null));
  const [summaryData, setSummaryData] = useState(() => readJson('mockInterview.summaryData', null));

  const handleStartInterview = (session) => {
    setSessionData(session);
    setCurrentScreen('interview');
  };

  const handleEndInterview = (summary) => {
    setSummaryData(summary);
    setCurrentScreen('summary');
  };

  const handleRestart = () => {
    if (sessionData?.session_id) {
      localStorage.removeItem(`mockInterview.state.${sessionData.session_id}`);
      localStorage.removeItem(`mockInterview.state.${sessionData.session_id}.start`);
    }
    localStorage.removeItem('mockInterview.currentScreen');
    localStorage.removeItem('mockInterview.sessionData');
    localStorage.removeItem('mockInterview.summaryData');
    setSessionData(null);
    setSummaryData(null);
    setCurrentScreen('form');
  };

  useEffect(() => {
    localStorage.setItem('mockInterview.currentScreen', currentScreen);
  }, [currentScreen]);

  useEffect(() => {
    if (sessionData) {
      localStorage.setItem('mockInterview.sessionData', JSON.stringify(sessionData));
    } else {
      localStorage.removeItem('mockInterview.sessionData');
    }
  }, [sessionData]);

  useEffect(() => {
    if (summaryData) {
      localStorage.setItem('mockInterview.summaryData', JSON.stringify(summaryData));
    } else {
      localStorage.removeItem('mockInterview.summaryData');
    }
  }, [summaryData]);

  return (
    <div className="mock-interview-iqra">
      <div className="mock-interview-iqra__container">
        {currentScreen === 'form' && (
          <InterviewForm
            onStartInterview={handleStartInterview}
            apiBaseUrl={API_BASE_URL}
          />
        )}
        {currentScreen === 'interview' && sessionData && (
          <InterviewScreen
            sessionData={sessionData}
            onEndInterview={handleEndInterview}
            onRestart={handleRestart}
            apiBaseUrl={API_BASE_URL}
          />
        )}
        {currentScreen === 'summary' && summaryData && (
          <SummaryScreen
            summaryData={summaryData}
            onRestart={handleRestart}
          />
        )}
      </div>
    </div>
  );
};

export default MockInterview;

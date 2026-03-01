import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import Chatbot from './Chatbot';
import './AIAssistant.css';

const AIAssistant = () => {
  const location = useLocation();
  const [askAssistantRequest, setAskAssistantRequest] = useState(null);

  useEffect(() => {
    if (location.state?.question) {
      const { question, skill, role, interviewType } = location.state;
      setAskAssistantRequest({
        question: question,
        context: {
          skill: skill || 'General',
          role: role || 'Candidate',
          interviewType: interviewType || 'Conceptual'
        },
        timestamp: Date.now()
      });
    }
  }, [location.state]);

  return (
    <div className="ai-assistant-page">
      <div className="ai-assistant-container">
        <div className="ai-assistant-header">
          <h1 className="page-title">AI Assistant</h1>
          <p className="page-subtitle">
            Get help with interview preparation, technical questions, and career guidance
          </p>
        </div>
        <div className="ai-assistant-content">
          <Chatbot isSidebar={true} askAssistantRequest={askAssistantRequest} />
        </div>
      </div>
    </div>
  );
};

export default AIAssistant;



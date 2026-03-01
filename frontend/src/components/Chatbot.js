import React, { useState, useRef, useEffect, useCallback } from 'react';
import { MessageCircle, X, Send, Bot, User, Mic, MicOff } from 'lucide-react';
import './Chatbot.css';
import { API_BASE_URL } from '../config';

const Chatbot = ({ currentQuestion, selectedSkill, selectedRole, interviewType, isSidebar = false, askAssistantRequest }) => {
  const [isOpen, setIsOpen] = useState(isSidebar); // Auto-open if sidebar
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const recognitionRef = useRef(null);
  const lastAssistantRequestRef = useRef(null);
  const renderFormattedLine = (line, lineIndex) => {
    if (!line) return null;

    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);
    const text = headingMatch ? headingMatch[2] : line;

    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    const content = parts.map((part, idx) => {
      const boldMatch = part.match(/^\*\*([^*]+)\*\*$/);
      if (boldMatch) {
        return <strong key={`${lineIndex}-bold-${idx}`}>{boldMatch[1]}</strong>;
      }
      return <React.Fragment key={`${lineIndex}-text-${idx}`}>{part}</React.Fragment>;
    });

    if (headingMatch) {
      return <span className="message-heading">{content}</span>;
    }

    return content;
  };

  // Initialize with welcome message (only if no askAssistantRequest)
  useEffect(() => {
    if (isOpen && messages.length === 0 && !askAssistantRequest) {
      setMessages([{
        role: 'assistant',
        content: `Hello! I'm your Interview Preparation Assistant. I'm specifically designed to help you prepare for interviews.\n\nI can assist you with:\n• Technical interview questions and concepts\n• Coding problems and algorithms\n• Behavioral interview tips and STAR method\n• Problem-solving strategies\n• Interview preparation advice\n• Resume and portfolio feedback\n\nPlease note: I focus exclusively on interview preparation topics. How can I help you prepare for your interview today?`
      }]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, askAssistantRequest]);

  // Auto scroll to bottom when new message arrives
  useEffect(() => {
    scrollToBottom();
  }, [messages.length]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Function to send message with text
  const handleSendMessageWithText = useCallback(async (text) => {
    if (!text || !text.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: text.trim()
    };

    setMessages(prev => [...prev, userMessage]);
    const messageToSend = text.trim();
    setInputMessage('');
    setIsLoading(true);

    try {
      const requestBody = {
        message: messageToSend,
        context: {
          currentQuestion: currentQuestion || null,
          skill: selectedSkill || null,
          role: selectedRole || null,
          interviewType: interviewType || null
        },
        conversationHistory: messages.slice(-10) // Last 10 messages for context
      };

      console.log('Sending chatbot request to:', `${API_BASE_URL}/api/chatbot`);
      console.log('Request body:', requestBody);

      const response = await fetch(`${API_BASE_URL}/api/chatbot`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const data = await response.json();
      console.log('Response data:', data);

      if (data.success) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.message || 'Sorry, I encountered an error. Please try again.'
        }]);
      }
    } catch (error) {
      console.error('Chatbot error:', error);
      let errorMessage = 'Sorry, I couldn\'t connect to the server. ';
      
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        errorMessage += 'Please make sure the backend server is running on port 5000.';
      } else if (error.message.includes('HTTP error')) {
        errorMessage += 'Server returned an error. Please try again.';
      } else {
        errorMessage += 'Please check your connection and try again.';
      }
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMessage
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [messages, isLoading, currentQuestion, selectedSkill, selectedRole, interviewType]);

  useEffect(() => {
    if (!askAssistantRequest) return;
    if (lastAssistantRequestRef.current === askAssistantRequest.timestamp) return;

    const { question, context } = askAssistantRequest;
    if (!question) return;

    lastAssistantRequestRef.current = askAssistantRequest.timestamp;

    const skillLabel = context?.skill || 'General';
    const roleLabel = context?.role || 'Candidate';
    const interviewLabel = context?.interviewType || 'Conceptual';

    // Clear existing messages first
    setMessages([]);

    const prompt = `Interview Preparation Question: ${question}\nSkill: ${skillLabel}\nRole: ${roleLabel}\nInterview Type: ${interviewLabel}\n\nPlease help me understand and answer this interview question effectively.`;

    const sendPrompt = () => {
      // handleSendMessageWithText will add the user message and send to backend
      handleSendMessageWithText(prompt);
    };

    if (!isOpen) {
      setIsOpen(true);
      setTimeout(sendPrompt, 250);
    } else {
      sendPrompt();
    }
  }, [askAssistantRequest, handleSendMessageWithText, isOpen]);

  // Initialize speech recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputMessage(transcript);
        setIsRecording(false);
        // Auto-send message after voice input
        setTimeout(() => {
          if (transcript.trim()) {
            handleSendMessageWithText(transcript);
          }
        }, 500);
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [handleSendMessageWithText]);

  const handleVoiceToggle = () => {
    if (isRecording) {
      // Stop recording
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsRecording(false);
    } else {
      // Start recording
      if (recognitionRef.current) {
        try {
          recognitionRef.current.start();
          setIsRecording(true);
        } catch (error) {
          console.error('Error starting speech recognition:', error);
        }
      }
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;
    
    await handleSendMessageWithText(inputMessage);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const clearChat = () => {
    setMessages([{
      role: 'assistant',
      content: `Hello! I'm your Interview Preparation Assistant. I'm specifically designed to help you prepare for interviews.\n\nI can assist you with:\n• Technical interview questions and concepts\n• Coding problems and algorithms\n• Behavioral interview tips and STAR method\n• Problem-solving strategies\n• Interview preparation advice\n• Resume and portfolio feedback\n\nPlease note: I focus exclusively on interview preparation topics. How can I help you prepare for your interview today?`
    }]);
  };

  return (
    <>
      {/* Floating Toggle Button - ChatGPT Style - Only show if not sidebar */}
      {!isSidebar && (
        <button
          className="chatbot-toggle-btn"
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? "Close chatbot" : "Open chatbot"}
        >
          {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className={`chatbot-container ${isSidebar ? 'chatbot-sidebar-mode' : ''}`}>
          <div className="chatbot-header">
            <div className="chatbot-header-content">
              <Bot size={20} />
              <div>
                <h3>Interview Assistant</h3>
                <p className="chatbot-subtitle">Focused on interview preparation only</p>
              </div>
            </div>
            <div className="chatbot-header-actions">
              <button
                className="chatbot-clear-btn"
                onClick={clearChat}
                title="Clear chat"
              >
                Clear
              </button>
            </div>
          </div>

          <div className="chatbot-messages" ref={chatContainerRef}>
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`chatbot-message ${msg.role === 'user' ? 'user-message' : 'assistant-message'}`}
              >
                <div className="message-avatar">
                  {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className="message-content">
                  {msg.content && (
                    <div className="message-text">
                      {msg.content.split('\n').map((line, i) => (
                        <React.Fragment key={i}>
                          {renderFormattedLine(line, i)}
                          {i < msg.content.split('\n').length - 1 && <br />}
                        </React.Fragment>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="chatbot-message assistant-message">
                <div className="message-avatar">
                  <Bot size={16} />
                </div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chatbot-input-container">
            <input
              type="text"
              className="chatbot-input"
              placeholder={isRecording ? "Listening..." : "Type your question..."}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading || isRecording}
            />
            <button
              className={`chatbot-voice-btn ${isRecording ? 'recording' : ''}`}
              onClick={handleVoiceToggle}
              title={isRecording ? 'Stop recording' : 'Start voice input'}
              style={{
                display: 'flex',
                visibility: 'visible',
                opacity: 1,
                width: '44px',
                height: '44px',
                minWidth: '44px',
                minHeight: '44px',
                backgroundColor: '#f0f0f0',
                border: '2px solid #2E86AB',
                borderRadius: '50%',
                cursor: 'pointer',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                zIndex: 100
              }}
            >
              {isRecording ? <MicOff size={18} /> : <Mic size={18} />}
            </button>
            <button
              className="chatbot-send-btn"
              onClick={handleSendMessage}
              disabled={!inputMessage.trim() || isLoading}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default Chatbot;


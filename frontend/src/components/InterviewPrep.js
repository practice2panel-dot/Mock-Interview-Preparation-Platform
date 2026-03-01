import React, { useState, useEffect, useRef } from 'react';
import { 
  ArrowLeft, 
  ArrowRight, 
  Mic, 
  MicOff,
  Edit3, 
  Volume2,
  Clock,
  Play,
  Pause,
  Square,
  Brain,
  BookOpen,
  Target,
  User,
  Send,
  CheckCircle,
  Loader2,
  Trophy,
  ThumbsUp,
  TrendingUp,
  TrendingDown,
  FileText,
  X,
  ChevronRight,
  Star,
  HelpCircle,
  MessageSquare
} from 'lucide-react';
import './InterviewPrep.css';
import './InterviewPrepLayout.css';
import { API_BASE_URL } from '../config';

const InterviewPrep = () => {
  // Selection screen state
  const [showSelectionScreen, setShowSelectionScreen] = useState(true);
  const [selectedRole, setSelectedRole] = useState('');
  const [selectedInterviewType, setSelectedInterviewType] = useState('');
  const [selectedSkill, setSelectedSkill] = useState('');
  const [currentStep, setCurrentStep] = useState('role'); // 'role' | 'type' | 'skill'

  // Interview state
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [inputMode, setInputMode] = useState('voice'); // 'text' or 'voice'
  const [isRecording, setIsRecording] = useState(false);
  const [textAnswer, setTextAnswer] = useState('');
  const [timer, setTimer] = useState(0);
  const [timerRunning, setTimerRunning] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [userMessage, setUserMessage] = useState('');
  const [recordingTime, setRecordingTime] = useState(0);
  const [maxTime] = useState(180); // 3 minutes
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [simpleAnswer, setSimpleAnswer] = useState('');
  const [showSimpleAnswer, setShowSimpleAnswer] = useState(false);
  const [showYourResponse, setShowYourResponse] = useState(false);
  const [showFeedbackSection, setShowFeedbackSection] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false); // Modal for "Try AI Assistant for Help"
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [availableVoices, setAvailableVoices] = useState([]);
  const utteranceRef = useRef(null);
  
  const timerIntervalRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);
  const audioRef = useRef(null);

  // Job roles with their skills
  const jobRoles = {
    'AI Engineer': {
      skills: ['Machine Learning', 'Python', 'TensorFlow', 'PyTorch', 'Deep Learning'],
      color: 'var(--primary-color)'
    },
    'Data Scientist': {
      skills: ['Python', 'Machine Learning', 'SQL', 'Data Analysis', 'Statistics'],
      color: 'var(--accent-color)'
    },
    'Python Developer': {
      skills: ['Python', 'AWS', 'Kubernetes', 'Docker', 'Lambda'],
      color: 'var(--secondary-color)'
    }
  };

  // Questions state
  const [questions, setQuestions] = useState([]);
  const [loadingQuestions, setLoadingQuestions] = useState(false);

  // Fetch questions from API
  useEffect(() => {
    if (!showSelectionScreen && selectedRole && selectedInterviewType && selectedSkill) {
      fetchQuestions();
    }
  }, [showSelectionScreen, selectedRole, selectedInterviewType, selectedSkill]);

  const fetchQuestions = async () => {
    try {
      setLoadingQuestions(true);
      const response = await fetch(`${API_BASE_URL}/api/questions/${selectedInterviewType}/${selectedSkill}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch questions');
      }
      
      const data = await response.json();
      
      if (data.success && data.questions && data.questions.length > 0) {
        const formattedQuestions = data.questions.map((q, idx) => ({
          id: idx + 1,
          question: q,
          category: selectedSkill
        }));
        setQuestions(formattedQuestions);
        setCurrentQuestionIndex(0);
      } else {
        setUserMessage('No questions available for this combination. Please try a different selection.');
        setQuestions([]);
      }
    } catch (error) {
      console.error('Error fetching questions:', error);
      setUserMessage('Failed to load questions. Please try again.');
      setQuestions([]);
    } finally {
      setLoadingQuestions(false);
    }
  };

  const currentQuestion = questions[currentQuestionIndex] || null;
  const totalQuestions = questions.length;

  // Handle skill select
  const handleSkillSelect = (skill) => {
    setSelectedSkill(skill);
    // Start interview when skill is selected
    setShowSelectionScreen(false);
    setCurrentQuestionIndex(0);
    setTimer(0);
    setTextAnswer('');
    setFeedback(null);
    setTranscript('');
    setUserMessage('');
    setSimpleAnswer('');
    setShowSimpleAnswer(false);
    setShowYourResponse(false);
    setShowFeedbackSection(false);
    setAudioBlob(null);
    setAudioUrl(null);
    setIsRecording(false);
    setIsPlaying(false);
  };

  // Auto-clear user messages
  useEffect(() => {
    if (userMessage) {
      const timer = setTimeout(() => {
        setUserMessage('');
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [userMessage]);

  // Timer effect
  useEffect(() => {
    if (timerRunning) {
      timerIntervalRef.current = setInterval(() => {
        setTimer(prev => prev + 1);
      }, 1000);
    } else {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    }
    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    };
  }, [timerRunning]);


  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Audio playback functions
  const playAudio = () => {
    if (audioUrl && audioRef.current) {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const pauseAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  };

  // Helper function to remove question numbers from text
  const removeQuestionNumber = (text) => {
    if (!text || !text.trim()) return text;
    // Remove patterns like "1.", "1)", "Question 1:", "Q1.", "Q1:", etc. from the start
    return text.replace(/^(?:question\s*)?\d+[\.\)\:]\s*/i, '').replace(/^q\d+[\.\)\:]\s*/i, '').trim();
  };

  // Text-to-speech functions
  const speakText = (text) => {
    if (!text || !text.trim()) return;
    if (!('speechSynthesis' in window)) {
      setUserMessage('Text-to-speech is not supported in this browser.');
      return;
    }

    // Remove question number before speaking
    const textToSpeak = removeQuestionNumber(text);
    if (!textToSpeak || !textToSpeak.trim()) return;

    const synth = window.speechSynthesis;
    
    // Stop any ongoing speech
    if (isSpeaking) {
      synth.cancel();
      setIsSpeaking(false);
      setIsPaused(false);
      utteranceRef.current = null;
      return;
    }

    // Create new utterance
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utteranceRef.current = utterance;
    
    // Select voice
    const preferred = availableVoices.find(v => /en-?US/i.test(v.lang)) || availableVoices[0];
    if (preferred) utterance.voice = preferred;
    
    // Configure speech
    utterance.rate = 0.9;
    utterance.pitch = 1;
    utterance.volume = 1;

    // Event handlers
    utterance.onstart = () => {
      setIsSpeaking(true);
      setIsPaused(false);
    };
    
    utterance.onend = () => {
      setIsSpeaking(false);
      setIsPaused(false);
      utteranceRef.current = null;
    };
    
    utterance.onerror = () => {
      setIsSpeaking(false);
      setIsPaused(false);
      utteranceRef.current = null;
    };

    // Reset and speak
    try { synth.cancel(); } catch (_) {}
    synth.speak(utterance);
  };

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      setIsPaused(false);
      utteranceRef.current = null;
    }
  };

  // Load available voices
  useEffect(() => {
    if (!('speechSynthesis' in window)) return;
    const synth = window.speechSynthesis;
    const loadVoices = () => {
      const voices = synth.getVoices();
      if (voices && voices.length) {
        setAvailableVoices(voices);
      }
    };
    loadVoices();
    synth.onvoiceschanged = loadVoices;
    return () => {
      if (synth) synth.onvoiceschanged = null;
    };
  }, []);

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      stopSpeaking();
      setCurrentQuestionIndex(currentQuestionIndex - 1);
      setTextAnswer('');
      setTranscript('');
      setFeedback(null);
      setSimpleAnswer('');
      setShowSimpleAnswer(false);
      setShowYourResponse(false);
      setShowFeedbackSection(false);
      setTimer(0);
      setTimerRunning(false);
      setIsRecording(false);
      setAudioBlob(null);
      setAudioUrl(null);
      setIsPlaying(false);
      setUserMessage('');
    }
  };

  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      stopSpeaking();
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setTextAnswer('');
      setTranscript('');
      setFeedback(null);
      setSimpleAnswer('');
      setShowSimpleAnswer(false);
      setShowYourResponse(false);
      setShowFeedbackSection(false);
      setTimer(0);
      setTimerRunning(false);
      setIsRecording(false);
      setAudioBlob(null);
      setAudioUrl(null);
      setIsPlaying(false);
      setUserMessage('');
    }
  };

  const handleVoiceToggle = () => {
    if (inputMode === 'voice') {
      setIsRecording(false);
      setTimerRunning(false);
      setInputMode('text');
    } else {
      setInputMode('voice');
    }
  };

  // Start voice recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const mime = (mediaRecorderRef.current && mediaRecorderRef.current.mimeType) || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: mime });
        setAudioBlob(audioBlob);
        setAudioUrl(URL.createObjectURL(audioBlob));
        stream.getTracks().forEach(track => track.stop());
        
        // Process the voice recording
        processVoiceRecording(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      setTimerRunning(true);
    } catch (error) {
      console.error('Error starting recording:', error);
      setUserMessage('Could not access microphone. Please check permissions.');
    }
  };

  // Stop voice recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setTimerRunning(false);
    }
  };

  const handleRecordToggle = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  // Process voice recording to get transcript and feedback
  const processVoiceRecording = async (audioBlob) => {
    try {
      setIsProcessing(true);
      setUserMessage('');
      
      const formData = new FormData();
      const filename = audioBlob.type && audioBlob.type.includes('wav') ? 'recording.wav' : 'recording.webm';
      formData.append('audio', audioBlob, filename);
      formData.append('question', currentQuestion.question || 'Practice question');
      
      const response = await fetch(`${API_BASE_URL}/api/process-voice`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success && data.transcript) {
        setTranscript(data.transcript);
        
        // Check if response is irrelevant BEFORE processing evaluation
        if (data.is_irrelevant === true || data.is_irrelevant === 'true') {
          setFeedback(null);
          setShowFeedbackSection(false);
          setShowHelpModal(true);
          return;
        }
        
        // If evaluation is included in response
        if (data.evaluation) {
          try {
            const parsed = typeof data.evaluation === 'string' ? JSON.parse(data.evaluation) : data.evaluation;
            
            // Double-check parsed evaluation for irrelevant flag
            if (parsed && (parsed.is_irrelevant === true || parsed.is_irrelevant === 'true')) {
              setFeedback(null);
              setShowFeedbackSection(false);
              setShowHelpModal(true);
              return;
            }
            
            setFeedback(parsed);
            setShowFeedbackSection(true);
          } catch (e) {
            setFeedback({ summary: 'Feedback received but could not be parsed.' });
          }
        }
        // If simple answer is provided
        if (data.simple_answer) {
          setSimpleAnswer(data.simple_answer);
          setShowSimpleAnswer(false);
        }
        setUserMessage('Voice processed successfully!');
      } else {
        setUserMessage(data.message || 'Voice processing failed.');
      }
    } catch (error) {
      console.error('Error processing voice:', error);
      setUserMessage('Could not connect to voice processing service. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Submit text answer for feedback
  const submitTextForFeedback = async () => {
    const questionText = currentQuestion.question || '';
    const answerText = textAnswer.trim();
    
    if (!questionText || !answerText) {
      setUserMessage('Please type your answer before submitting.');
      return;
    }
    
    try {
      setIsProcessing(true);
      setUserMessage('');
      
      const response = await fetch(`${API_BASE_URL}/api/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: questionText,
          answer: answerText,
          job_title: selectedRole || 'Software Engineer',
          skills: selectedSkill || '',
          interview_type: selectedInterviewType || ''
        })
      });
      
      const data = await response.json();
      
      if (data && data.success) {
        // Check if response is irrelevant BEFORE processing evaluation
        if (data.is_irrelevant === true || data.is_irrelevant === 'true') {
          setFeedback(null);
          setShowFeedbackSection(false);
          setShowHelpModal(true);
          return;
        }
        
        let parsed = null;
        try {
          parsed = typeof data.evaluation === 'string' ? JSON.parse(data.evaluation) : data.evaluation;
        } catch (_) {
          parsed = data.evaluation || null;
        }
        
        // Double-check parsed evaluation for irrelevant flag
        if (parsed && (parsed.is_irrelevant === true || parsed.is_irrelevant === 'true')) {
          setFeedback(null);
          setShowFeedbackSection(false);
          setShowHelpModal(true);
          return;
        }
        
        if (parsed) {
          setFeedback(parsed);
          setShowFeedbackSection(true);
          setUserMessage('Feedback generated successfully!');
        } else {
          setUserMessage('Feedback received but could not be parsed.');
        }
      } else {
        setUserMessage(data.message || 'Failed to evaluate answer.');
      }
    } catch (error) {
      console.error('Error submitting answer:', error);
      setUserMessage('Could not connect to evaluation service.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Recording timer effect
  useEffect(() => {
    if (isRecording) {
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => {
          if (prev >= maxTime) {
            stopRecording();
            return maxTime;
          }
          return prev + 1;
        });
      }, 1000);
    } else {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
    }

    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
    };
  }, [isRecording, maxTime]);


  // Show selection screen
  if (showSelectionScreen) {
    return (
      <div className="interview-prep">
        <div className="skill-prep">
          <div className="container">
            <div className="skill-prep-header">
              <h1 className="section-title">AI Interview Practice</h1>
              <p className="section-subtitle">
                Practice with real interview questions and get instant feedback
              </p>
            </div>

            <div className="setup-container">
              <div className="setup-card card">
                {currentStep === 'role' && (
                  <div className="setup-section">
                    <h3>1. Choose Your Job Role</h3>
                    <div className="role-options vertical-list">
                      {Object.entries(jobRoles).map(([role, data]) => (
                        <button
                          key={role}
                          className={`role-option ${selectedRole === role ? 'selected' : ''}`}
                          onClick={() => {
                            setSelectedRole(role);
                            setCurrentStep('type');
                          }}
                          style={{ '--role-color': data.color }}
                        >
                          <div className="role-color-indicator"></div>
                          <span>{role}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {currentStep === 'type' && selectedRole && (
                  <div className="setup-section">
                    <h3>2. Select Interview Type</h3>
                    <div className="interview-type-options vertical-list">
                      {[
                        { value: 'technical', label: 'Technical Interview', icon: <Brain size={20} /> },
                        { value: 'conceptual', label: 'Conceptual Interview', icon: <BookOpen size={20} /> },
                        { value: 'behavioral', label: 'Behavioral Interview', icon: <User size={20} /> }
                      ].map((type) => (
                        <button
                          key={type.value}
                          className={`interview-type-option ${type.value} ${selectedInterviewType === type.value ? 'selected' : ''}`}
                          onClick={() => {
                            setSelectedInterviewType(type.value);
                            setCurrentStep('skill');
                          }}
                        >
                          {type.icon}
                          <span>{type.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {currentStep === 'skill' && selectedRole && selectedInterviewType && (
                  <div className="setup-section">
                    <h3>3. Select a Skill</h3>
                    <div className="skill-options vertical-list">
                      {jobRoles[selectedRole].skills.map((skill) => (
                        <button
                          key={skill}
                          className={`skill-option ${selectedSkill === skill ? 'selected' : ''}`}
                          onClick={() => handleSkillSelect(skill)}
                        >
                          <BookOpen size={20} />
                          <span>{skill}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Show interview questions interface
  if (loadingQuestions) {
    return (
      <div className="interview-prep">
        <div className="interview-dashboard">
          <div className="question-panel">
            <div className="question-card card">
              <div style={{ textAlign: 'center', padding: '3rem' }}>
                <Loader2 size={48} className="animate-spin" style={{ margin: '0 auto 1rem' }} />
                <p>Loading questions...</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!currentQuestion || questions.length === 0) {
    return (
      <div className="interview-prep">
        <div className="interview-dashboard">
          <div className="question-panel">
            <div className="question-card card">
              <div style={{ textAlign: 'center', padding: '3rem' }}>
                <p>No questions available. Please go back and select different options.</p>
                <button 
                  className="nav-btn prev-btn"
                  onClick={() => {
                    setShowSelectionScreen(true);
                    setCurrentStep('role');
                    setSelectedRole('');
                    setSelectedInterviewType('');
                    setSelectedSkill('');
                  }}
                  style={{ marginTop: '1rem' }}
                >
                  Go Back
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="interview-prep">
      <div className="interview-dashboard">
        {questions.length > 0 ? (
          <div className="question-panel">
            <div className="question-card card">
              {/* Header with badges */}
              <div className="question-header">
                <span className="question-badge">QUESTION {currentQuestion.id} OF {totalQuestions}</span>
                <span className="timer-badge">
                  <Clock size={14} />
                  {formatTime(timer)} / 3:00
                </span>
              </div>

              {/* Question Content */}
              <div className="question-content">
              <div className="question-text-wrapper">
                <h2 className="question-text">Q{currentQuestion.id}. {currentQuestion.question}</h2>
                <button 
                  className="speaker-btn" 
                  title="Play question audio"
                  onClick={() => speakText(currentQuestion.question)}
                >
                  {isSpeaking ? <Square size={20} /> : <Volume2 size={20} />}
                </button>
              </div>
            </div>

            {/* Answer Options */}
            <div className="answer-options">
              <button
                className={`answer-mode-btn voice-btn ${inputMode === 'voice' ? 'active' : ''}`}
                onClick={() => setInputMode('voice')}
              >
                <Mic size={20} />
                <span>Voice Answer</span>
              </button>
              <button
                className={`answer-mode-btn type-btn ${inputMode === 'text' ? 'active' : ''}`}
                onClick={() => setInputMode('text')}
              >
                <Edit3 size={20} />
                <span>Type Answer</span>
              </button>
            </div>

              {/* Voice Controls (for voice mode) */}
              {inputMode === 'voice' && (
                <div className="voice-controls">
                  <button
                    className={`voice-button ${isRecording ? 'recording' : ''}`}
                    onClick={handleRecordToggle}
                    disabled={isProcessing}
                  >
                    {isRecording ? <MicOff size={32} /> : <Mic size={32} />}
                  </button>
                  
                  {audioUrl && (
                    <button
                      className="play-button"
                      onClick={isPlaying ? pauseAudio : playAudio}
                    >
                      {isPlaying ? <Pause size={20} /> : <Play size={20} />}
                    </button>
                  )}
                  
                  {isProcessing && (
                    <div className="processing-indicator">
                      <Loader2 size={20} className="animate-spin" />
                      <span>Processing voice...</span>
                    </div>
                  )}
                </div>
              )}

              {/* Status */}
              <div className="recording-status">
                {inputMode === 'voice' ? (
                  isRecording ? (
                    <div className="status-recording">
                      <div className="pulse-dot"></div>
                      <span>Recording... {formatTime(recordingTime)} / {formatTime(maxTime)}</span>
                    </div>
                  ) : null
                ) : (
                  textAnswer.trim() ? (
                    <div className="status-complete">
                      <CheckCircle size={16} />
                      <span>Answer ready!</span>
                    </div>
                  ) : null
                )}
              </div>

              {/* Text Input Section (for text mode) */}
              {inputMode === 'text' && (
                <div className="text-input-section">
                  <textarea
                    className="text-answer-input"
                    placeholder="Type your answer here..."
                    value={textAnswer}
                    onChange={(e) => setTextAnswer(e.target.value)}
                    rows={6}
                    disabled={isProcessing}
                  />
                  <button
                    className="send-btn"
                    title={isProcessing ? 'Submitting...' : 'Submit'}
                    onClick={(e) => { e.preventDefault(); submitTextForFeedback(); }}
                    disabled={isProcessing || !textAnswer.trim()}
                  >
                    {isProcessing ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                  </button>
                </div>
              )}

              {/* User Message */}
              {userMessage && (
                <div className="user-message">
                  <div className="message-content">
                    <HelpCircle size={18} />
                    <span>{userMessage}</span>
                    <button 
                      className="message-close"
                      onClick={() => setUserMessage('')}
                      aria-label="Close message"
                    >
                      ×
                    </button>
                  </div>
                </div>
              )}

              {/* Simple Answer Section (collapsible) */}
              {simpleAnswer && (
                <div className="simple-answer-container">
                  <div 
                    className="simple-answer-header"
                    onClick={() => setShowSimpleAnswer(!showSimpleAnswer)}
                  >
                    <div className="simple-answer-title">
                      <BookOpen size={20} />
                      <span>Simple Answer</span>
                      <span className="ready-badge">Click to view</span>
                    </div>
                    <div className="header-actions">
                      <button
                        className="voice-play-button"
                        onClick={(e) => {
                          e.stopPropagation();
                          speakText(simpleAnswer);
                        }}
                        title={isSpeaking ? "Stop speaking" : "Listen to answer"}
                      >
                        {isSpeaking ? <Square size={16} /> : <Volume2 size={16} />}
                      </button>
                      <ChevronRight 
                        size={20} 
                        className={`chevron ${showSimpleAnswer ? 'expanded' : ''}`}
                      />
                    </div>
                  </div>
                  
                  {showSimpleAnswer && (
                    <div className="simple-answer-content">
                      <div className="simple-answer-text">{simpleAnswer}</div>
                    </div>
                  )}
                </div>
              )}

              {/* Your Response (collapsible) */}
              {transcript && (
                <div className="your-response-container">
                  <div className="simple-answer-header" onClick={() => setShowYourResponse(!showYourResponse)}>
                    <div className="simple-answer-title">
                      <Edit3 size={20} />
                      <span>Your Response</span>
                      <span className="ready-badge">Click to view</span>
                    </div>
                    <div className="header-actions">
                      <button
                        className="voice-play-button"
                        onClick={(e) => { 
                          e.stopPropagation(); 
                          speakText(transcript); 
                        }}
                        title={isSpeaking ? "Stop speaking" : "Listen to your response"}
                      >
                        {isSpeaking ? <Square size={16} /> : <Volume2 size={16} />}
                      </button>
                      <ChevronRight size={20} className={`chevron ${showYourResponse ? 'expanded' : ''}`} />
                    </div>
                  </div>
                  {showYourResponse && (
                    <div className="simple-answer-content">
                      <div className="simple-answer-text">{transcript}</div>
                    </div>
                  )}
                </div>
              )}

              {/* Feedback Section (collapsible) */}
              {feedback && (
                <div className="feedback-section-container">
                  <div className="simple-answer-header" onClick={() => setShowFeedbackSection(!showFeedbackSection)}>
                    <div className="simple-answer-title">
                      <Trophy size={20} />
                      <span>AI Feedback</span>
                      <span className="ready-badge">Click to view</span>
                    </div>
                    <div className="header-actions">
                      <ChevronRight size={20} className={`chevron ${showFeedbackSection ? 'expanded' : ''}`} />
                    </div>
                  </div>
                  {showFeedbackSection && (
                    <div className="feedback-section-content">
                      <div className="feedback-card-container practice-feedback">
                        <div className="feedback-card-body">
                          {typeof feedback.score !== 'undefined' && (
                            <div className="feedback-card-item feedback-score-card">
                              <div className="feedback-item-header">
                                <Star className="feedback-item-icon score-icon" size={20} />
                                <strong>Score</strong>
                              </div>
                              <div className="feedback-score-value">
                                <span className="score-number">{feedback.score}</span>
                                <span className="score-divider">/</span>
                                <span className="score-total">10</span>
                              </div>
                            </div>
                          )}
                          
                          {feedback.strengths && feedback.strengths.length > 0 && (
                            <div className="feedback-card-item feedback-strengths-card">
                              <div className="feedback-item-header">
                                <ThumbsUp className="feedback-item-icon strengths-icon" size={20} />
                                <strong>Strengths</strong>
                              </div>
                              <ul className="feedback-list">
                                {feedback.strengths.map((s, i) => (
                                  <li key={i}>
                                    <CheckCircle className="list-icon" size={16} />
                                    {s}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          
                          {feedback.improvements && feedback.improvements.length > 0 && (
                            <div className="feedback-card-item feedback-improvements-card">
                              <div className="feedback-item-header">
                                <TrendingDown className="feedback-item-icon improvements-icon" size={20} />
                                <strong>Areas for Improvement</strong>
                              </div>
                              <ul className="feedback-list">
                                {feedback.improvements.map((s, i) => (
                                  <li key={i}>
                                    <TrendingUp className="list-icon" size={16} />
                                    {s}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          
                          {feedback.summary && (
                            <div className="feedback-card-item feedback-summary-card">
                              <div className="feedback-item-header">
                                <FileText className="feedback-item-icon summary-icon" size={20} />
                                <strong>Summary</strong>
                              </div>
                              <p className="feedback-summary-text">{feedback.summary}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Audio element for playback */}
              <audio
                ref={audioRef}
                src={audioUrl}
                onEnded={() => setIsPlaying(false)}
                onPause={() => setIsPlaying(false)}
              />

              {/* Navigation Buttons */}
              <div className="navigation-buttons">
                <button
                  className="nav-btn prev-btn"
                  onClick={handlePrevious}
                  disabled={currentQuestionIndex === 0}
                >
                  <ArrowLeft size={20} />
                  <span>Previous</span>
                </button>
                <button
                  className="nav-btn next-btn"
                  onClick={handleNext}
                  disabled={currentQuestionIndex === questions.length - 1}
                >
                  <span>Next</span>
                  <ArrowRight size={20} />
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="no-questions-container">
            <div className="no-questions-card card">
              <h3>No Questions Available</h3>
              <p>There are no interview questions available for this combination.</p>
            </div>
          </div>
        )}

        {/* Help Modal - "Try AI Assistant for Help" */}
        {showHelpModal && (
          <div className="help-modal-overlay" onClick={() => setShowHelpModal(false)}>
            <div className="help-modal-container" onClick={(e) => e.stopPropagation()}>
              <div className="help-modal-header">
                <div className="help-modal-title">
                  <HelpCircle className="help-icon" size={28} />
                  <h3>Need Help?</h3>
                </div>
                <button 
                  className="help-modal-close"
                  onClick={() => setShowHelpModal(false)}
                  aria-label="Close help modal"
                >
                  <X size={24} />
                </button>
              </div>
              
              <div className="help-modal-body">
                <div className="help-message-card">
                  <MessageSquare className="help-message-icon" size={48} />
                  <h4>Try AI Assistant for Help</h4>
                  <p>
                    Your response seems unrelated to the question. Use the AI Assistant feature 
                    to get guidance on how to answer interview questions effectively.
                  </p>
                </div>
              </div>
              
              <div className="help-modal-footer">
                <button 
                  className="btn btn-primary"
                  onClick={() => setShowHelpModal(false)}
                >
                  Got it!
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default InterviewPrep;


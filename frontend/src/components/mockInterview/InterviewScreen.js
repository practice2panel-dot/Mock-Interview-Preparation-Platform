import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { useSpeech } from '../../hooks/useSpeech';

const InterviewScreen = ({ sessionData, onEndInterview, onRestart, apiBaseUrl }) => {
  const [currentQuestion, setCurrentQuestion] = useState(sessionData.first_question || '');
  const [feedback, setFeedback] = useState('');
  const [hint, setHint] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [isFollowUp, setIsFollowUp] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [voiceMode] = useState(true);

  const { speak, startListening, stopListening, listening, supported } = useSpeech();
  const [transcript, setTranscript] = useState('');
  const transcriptRef = useRef(''); // Store latest transcript in ref for reliable access
  const [micCooldownUntil, setMicCooldownUntil] = useState(0);
  const lastSpokenQuestionRef = useRef('');
  const welcomeSpokenRef = useRef(false);

  // Simple session timer
  const [elapsedMs, setElapsedMs] = useState(0);
  const sessionEndRef = useRef(false);
  const sessionLimitMs = 10 * 60 * 1000;
  const storageKey = `mockInterview.state.${sessionData.session_id}`;
  const startTimeRef = useRef(Date.now());
  useEffect(() => {
    const startKey = `${storageKey}.start`;
    const savedStart = localStorage.getItem(startKey);
    if (savedStart && !Number.isNaN(Number(savedStart))) {
      startTimeRef.current = Number(savedStart);
    } else {
      startTimeRef.current = Date.now();
      localStorage.setItem(startKey, String(startTimeRef.current));
    }
    setElapsedMs(Date.now() - startTimeRef.current);
    const id = setInterval(() => setElapsedMs(Date.now() - startTimeRef.current), 1000);
    return () => clearInterval(id);
  }, [storageKey]);

  useEffect(() => {
    const savedState = localStorage.getItem(storageKey);
    if (!savedState) return;
    try {
      const parsed = JSON.parse(savedState);
      if (parsed.currentQuestion) setCurrentQuestion(parsed.currentQuestion);
      if (parsed.feedback) setFeedback(parsed.feedback);
      if (parsed.hint) setHint(parsed.hint);
      if (parsed.questionNumber) setQuestionNumber(parsed.questionNumber);
      if (typeof parsed.isFollowUp === 'boolean') setIsFollowUp(parsed.isFollowUp);
      if (typeof parsed.isCompleted === 'boolean') setIsCompleted(parsed.isCompleted);
    } catch (e) {
      // ignore invalid cached state
    }
  }, [storageKey]);

  const formattedTime = useMemo(() => {
    const totalSeconds = Math.floor(elapsedMs / 1000);
    const h = String(Math.floor(totalSeconds / 3600)).padStart(2, '0');
    const m = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0');
    const s = String(totalSeconds % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
  }, [elapsedMs]);

  const remainingTime = useMemo(() => {
    const remaining = Math.max(0, sessionLimitMs - elapsedMs);
    const totalSeconds = Math.floor(remaining / 1000);
    const m = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
    const s = String(totalSeconds % 60).padStart(2, '0');
    return `${m}:${s}`;
  }, [elapsedMs, sessionLimitMs]);

  const statusText = useMemo(() => {
    if (listening) return 'Listening… tap mic to stop';
    return '';
  }, [listening]);

  const handleEndInterview = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${apiBaseUrl}/api/mock-interview/end`, {
        session_id: sessionData.session_id
      });
      onEndInterview(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to end interview. Please try again.');
      setLoading(false);
    }
  }, [apiBaseUrl, onEndInterview, sessionData.session_id]);

  useEffect(() => {
    if (sessionEndRef.current || isCompleted) return;
    if (elapsedMs >= sessionLimitMs) {
      sessionEndRef.current = true;
      handleEndInterview();
    }
  }, [elapsedMs, sessionLimitMs, isCompleted, handleEndInterview]);

  // Speak welcome (behavioral only) and every new question in voice mode
  useEffect(() => {
    if (!voiceMode || !currentQuestion) return;

    const speakQuestion = async () => {
      const isBehavioral = sessionData.interview_type?.toLowerCase() === 'behavioral';
      const isFirstQuestion = questionNumber === 1 && !isFollowUp;

      if (isBehavioral && isFirstQuestion && sessionData.welcome_message && !welcomeSpokenRef.current) {
        welcomeSpokenRef.current = true;
        await speak(sessionData.welcome_message);
      }

      if (lastSpokenQuestionRef.current !== currentQuestion) {
        const intro = isFollowUp ? 'Follow up question.' : `Question ${questionNumber}.`;
        await speak(`${intro} ${currentQuestion}`);
        lastSpokenQuestionRef.current = currentQuestion;
      }
    };

    speakQuestion();
  }, [currentQuestion, voiceMode, isFollowUp, questionNumber, sessionData, speak]);

  // Reset transcript when question changes
  useEffect(() => {
    setTranscript('');
    transcriptRef.current = '';
  }, [currentQuestion]);

  useEffect(() => {
    const state = {
      currentQuestion,
      feedback,
      hint,
      questionNumber,
      isFollowUp,
      isCompleted
    };
    localStorage.setItem(storageKey, JSON.stringify(state));
  }, [storageKey, currentQuestion, feedback, hint, questionNumber, isFollowUp, isCompleted]);

  const handleInteract = async (userInput) => {
    setLoading(true);
    setError(null);
    setHint('');
    setFeedback('');

    try {
      const response = await axios.post(`${apiBaseUrl}/api/mock-interview/interact`, {
        session_id: sessionData.session_id,
        user_input: userInput
      });

      const intent = response.data.intent || 'normal_answer'; // Default to normal_answer if intent not provided

      // Handle different intents
      if (intent === 'repeat_question') {
        setCurrentQuestion(response.data.question);
        setFeedback(response.data.message);
      } else if (intent === 'hint_request') {
        const h = response.data.hint;
        setHint(h);
        const msg = response.data.message || '';
        setFeedback(msg);
        if (voiceMode && h) {
          await speak(`Here's a hint: ${h}`);
        }
      } else if (intent === 'need_time') {
        setFeedback(response.data.message);
        if (voiceMode && response.data.message) {
          await speak(response.data.message);
        }
        // Optionally show a pause indicator
        if (response.data.pause_seconds) {
          setTimeout(() => {
            const ready = 'Ready when you are!';
            setFeedback(ready);
            if (voiceMode) {
              void speak(ready);
            }
          }, response.data.pause_seconds * 1000);
        }
      } else if (intent === 'normal_answer') {
        // Handle answer submission
        const fb = response.data.feedback || response.data.message || 'Thank you for your answer.';
        setFeedback(fb);

        // Speak feedback first, then wait for it to finish before speaking next question
        if (voiceMode && fb) {
          await speak(fb);
        }

        if (response.data.next_question || response.data.follow_up_question) {
          const nextQ = response.data.next_question || response.data.follow_up_question;

          // Update state first (isFollowUp and questionNumber) so useEffect has correct values
          if (response.data.is_followup) {
            setIsFollowUp(true);
          } else {
            setIsFollowUp(false);
            if (response.data.question_number) {
              setQuestionNumber(response.data.question_number);
            } else {
              setQuestionNumber(prev => prev + 1);
            }
          }

          // Set current question last - this will trigger useEffect to speak it
          // But feedback has already finished, so it won't be interrupted
          setCurrentQuestion(nextQ);
        }

        // Check if interview completed
        if (response.data.completed) {
          setIsCompleted(true);
          const endResponse = await axios.post(`${apiBaseUrl}/api/mock-interview/end`, {
            session_id: sessionData.session_id
          });
          onEndInterview(endResponse.data);
          return;
        }
      } else {
        // Fallback for unknown intent
        const msg = response.data.message || response.data.feedback || 'Processing your response...';
        setFeedback(msg);
        if (voiceMode) await speak(msg);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleMicClick = () => {
    const now = Date.now();
    if (now < micCooldownUntil) return; // debounce rapid toggles / phantom taps
    setMicCooldownUntil(now + 600);
    if (!supported.stt) {
      setError('Speech recognition is not supported in this browser.');
      return;
    }
    if (loading) {
      return; // ignore while processing
    }
    if (listening) {
      stopListening();
      // Use ref value to get the latest accumulated transcript
      const text = transcriptRef.current.trim();
      if (text) {
        console.log('Submitting transcript:', text); // Debug log
        handleInteract(text);
      } else {
        setError('No speech detected. Please try again.');
      }
    } else {
      setTranscript('');
      transcriptRef.current = '';
      startListening((text) => {
        // Update both state (for display) and ref (for reliable access)
        const trimmed = (text || '').trim();
        setTranscript(trimmed);
        transcriptRef.current = trimmed;
      });
    }
  };

  return (
    <div className="mock-interview-screen">
      <div className="question-card" style={{ marginBottom: 16 }}>
        <h3>{isFollowUp ? 'Follow-up Question' : `Question ${questionNumber} of ${sessionData.total_questions}`}</h3>
        <p>{currentQuestion || 'Loading question...'}</p>
      </div>
      {/* Controls */}
      <div className="mock-interview-actions-card">
        <div className="mock-interview-actions">
          <div className="mock-interview-actions__left">
            <button
              type="button"
              className="secondary-button"
              onClick={onRestart}
              disabled={loading}
            >
              Restart Interview
            </button>
          </div>

          {!isCompleted && (
            <div className="mock-interview-actions__right">
              <button
                type="button"
                className="primary-button"
                onClick={async () => {
                  try {
                    setLoading(true);
                    const res = await axios.post(`${apiBaseUrl}/api/mock-interview/next-question`, { session_id: sessionData.session_id });
                    const nextQ = res.data.next_question;
                    if (nextQ) {
                      setIsFollowUp(false);
                      if (res.data.question_number) setQuestionNumber(res.data.question_number);
                      // Set current question last - this will trigger useEffect to speak it
                      setCurrentQuestion(nextQ);
                    } else if (res.data.completed) {
                      setIsCompleted(true);
                      const endResponse = await axios.post(`${apiBaseUrl}/api/mock-interview/end`, { session_id: sessionData.session_id });
                      onEndInterview(endResponse.data);
                    }
                  } catch (e) {
                    setError(e.response?.data?.error || 'Failed to load next question');
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading}
              >
                Next Question
              </button>
              <button
                type="button"
                className="secondary-button danger-button"
                onClick={handleEndInterview}
                disabled={loading}
              >
                End Interview
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="session-header">
        <h1>AI Interview Session</h1>
        <div className="timer">
          <span role="img" aria-label="timer">⏲️</span>&nbsp; {formattedTime}
          <span style={{ marginLeft: 10 }}>Remaining: {remainingTime}</span>
        </div>
      </div>

      <div className="cards-grid">
        <div className="agent-card">
          <div className="agent-avatar">AR</div>
          <div className="agent-label">AI Recruiter</div>
        </div>
        <div className="user-card" onPointerDown={handleMicClick} style={{ cursor: loading ? 'not-allowed' : 'pointer', position: 'relative' }}>
          <div className={listening ? 'mic-icon mic-active' : 'mic-icon'}>
            🎤
          </div>
          <div className="mic-hint">{listening ? 'Tap to stop' : 'Tap to speak'}</div>
        </div>
      </div>

      {sessionData.welcome_message && sessionData.interview_type?.toLowerCase() === 'behavioral' && questionNumber === 1 && (
        <div className="feedback-card" style={{ marginBottom: 16 }}>
          <p className="feedback-text"><strong>Welcome:</strong> {sessionData.welcome_message}</p>
        </div>
      )}

      {statusText && (
        <div className="status-row">
          <div className={loading ? 'spinner' : 'dot'} />
          <span>{statusText}</span>
        </div>
      )}

      {listening && transcript && (
        <div className="transcript-preview">
          <strong>Your response:</strong> {transcript}
        </div>
      )}

      {feedback && (
        <div className="feedback-card">
          <p className="feedback-text"><strong>AI Feedback:</strong> {feedback}</p>
        </div>
      )}

      {hint && (
        <div className="hint-card">
          <p className="hint-text"><strong>Hint:</strong> {hint}</p>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {isCompleted && (
        <div className="loading">
          <p>Interview completed! Generating summary...</p>
        </div>
      )}
    </div>
  );
};

export default InterviewScreen;

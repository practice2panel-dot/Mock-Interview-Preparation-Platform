import { useEffect, useRef, useState, useCallback } from 'react';

// Simple speech hook using the Web Speech API (Chrome/Edge). Fallbacks are no-ops.
export function useSpeech() {
  const synthesis = typeof window !== 'undefined' ? window.speechSynthesis : null;
  const Recognition = typeof window !== 'undefined' 
    ? (window.SpeechRecognition || window.webkitSpeechRecognition) 
    : null;

  const recognitionRef = useRef(null);
  const [listening, setListening] = useState(false);
  const supported = { stt: !!Recognition, tts: !!synthesis };

  // Speak text via TTS - returns a Promise that resolves when speech finishes
  const speak = useCallback((text) => {
    if (!text || !synthesis) return Promise.resolve();
    return new Promise((resolve) => {
      try {
        synthesis.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.rate = 1; // natural rate
        utter.pitch = 1;
        utter.lang = 'en-US';
        
        utter.onend = () => resolve();
        utter.onerror = () => resolve();
        
        synthesis.speak(utter);
      } catch (_) {
        resolve();
      }
    });
  }, [synthesis]);

  // Start listening and stream the transcript via callback
  const startListening = useCallback((onTranscript) => {
    if (!Recognition) return;
    try {
      // Create new recognition instance each time to avoid stale state
      const rec = new Recognition();
      rec.lang = 'en-US';
      rec.interimResults = true; // Get real-time updates
      rec.continuous = true; // Keep listening through pauses
      rec.maxAlternatives = 1;

      let accumulatedTranscript = '';

      rec.onresult = (event) => {
        // Accumulate all results
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          if (result && result[0]) {
            const transcript = result[0].transcript;
            if (result.isFinal) {
              finalTranscript += transcript + ' ';
            } else {
              interimTranscript += transcript;
            }
          }
        }

        // Update accumulated transcript with final results
        if (finalTranscript) {
          accumulatedTranscript += finalTranscript;
        }

        // Call callback with accumulated + current interim (even if empty, to show progress)
        const fullTranscript = (accumulatedTranscript + interimTranscript).trim();
        if (onTranscript) {
          // Always call callback, even with empty string, so UI can show listening state
          onTranscript(fullTranscript || '');
        }
      };

      rec.onend = () => {
        // If recognitionRef.current is still this instance, we didn't explicitly stop
        // Restart recognition to continue listening through natural pauses
        if (recognitionRef.current === rec) {
          try {
            rec.start();
          } catch (e) {
            // If restart fails, stop listening
            setListening(false);
          }
        } else {
          // We explicitly stopped (recognitionRef.current was set to null)
          setListening(false);
        }
      };

      rec.onerror = (event) => {
        console.log('[Speech Recognition] Error:', event.error);
        // Don't stop on errors unless it's a critical error
        if (event.error === 'no-speech') {
          // This is normal - just silence, don't stop
          // Continue listening
          return;
        }
        if (event.error === 'not-allowed') {
          console.error('[Speech Recognition] Microphone permission denied');
          if (recognitionRef.current === rec) {
            setListening(false);
          }
          return;
        }
        if (event.error === 'aborted' || event.error === 'network') {
          // These are usually recoverable, try to continue
          return;
        }
        // For other errors, stop listening
        if (recognitionRef.current === rec) {
          setListening(false);
        }
      };

      recognitionRef.current = rec;
      rec.start();
      setListening(true);
    } catch (_) {
      setListening(false);
    }
  }, [Recognition]);

  const stopListening = useCallback(() => {
    try {
      if (recognitionRef.current) {
        // Set ref to null first to signal explicit stop
        const rec = recognitionRef.current;
        recognitionRef.current = null;
        rec.stop();
        setListening(false);
      }
    } catch (_) {
      setListening(false);
    }
  }, []);

  // Cleanup
  useEffect(() => () => {
    try {
      recognitionRef.current && recognitionRef.current.abort();
    } catch (_) {}
  }, []);

  return { speak, startListening, stopListening, listening, supported };
}


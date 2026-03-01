import os
import tempfile
import re
import json
from dotenv import load_dotenv
import logging
from typing import Optional

from rubric_loader import load_rubric_text
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global whisper model instance
whisper_model = None
openai_client: Optional[OpenAI] = None

def get_whisper_model():
    """Get or initialize the Whisper model"""
    global whisper_model
    if whisper_model is None:
        try:
            # Lazy import so backend can start without whisper installed
            import whisper  # type: ignore
        except ImportError as e:
            logger.error("Whisper is not installed. Install 'openai-whisper' to enable voice features.")
            raise
        logger.info("Loading Whisper model...")
        whisper_model = whisper.load_model("base")
    return whisper_model


def get_openai_client() -> OpenAI:
    global openai_client
    if openai_client is None:
        openai_client = OpenAI()
    return openai_client

def transcribe_audio(audio_file_path):
    """Transcribe audio using local Whisper; on failure, fall back to OpenAI API if available."""
    # First: local whisper
    try:
        model = get_whisper_model()
        result = model.transcribe(audio_file_path)
        return result["text"]
    except Exception as e:
        logger.error(f"Local Whisper transcription error: {e}")

    # Fallback: OpenAI Whisper API
    try:
        api_key_present = bool(os.getenv("OPENAI_API_KEY"))
        if not api_key_present:
            logger.error("OPENAI_API_KEY not set; cannot use OpenAI Whisper fallback.")
            return None
        client = get_openai_client()
        with open(audio_file_path, "rb") as f:
            tr = client.audio.transcriptions.create(
                model=os.getenv("OPENAI_STT_MODEL", "whisper-1"),
                file=f
            )
        text = getattr(tr, "text", None) or (tr.get("text") if isinstance(tr, dict) else None)
        if not text:
            logger.error("OpenAI Whisper API returned no text.")
            return None
        return text
    except Exception as e:
        logger.error(f"OpenAI Whisper API transcription error: {e}")
        return None

def process_text_response(text_response, question, job_title="Software Engineer", skills="Python, React", interview_type=""):
    """Process text response using LLM and rubric-derived criteria."""
    try:
        # First, check for "I don't know" patterns directly in the response (case-insensitive)
        text_lower = text_response.lower().strip()
        
        # Remove punctuation and extra spaces for better matching
        text_normalized = re.sub(r'[^\w\s]', '', text_lower)
        text_normalized = re.sub(r'\s+', ' ', text_normalized)
        
        irrelevant_patterns = [
            "i dont know", "i don't know", "idont know", "idon't know", "idonot know",
            "i have no idea", "i have no clue", "no idea", "no clue",
            "im not sure", "i'm not sure", "i am not sure",
            "i dont have", "i don't have", "i do not know",
            "i cannot answer", "i cant answer", "i can't answer",
            "i dont remember", "i don't remember",
            "im unsure", "i'm unsure", "unsure",
            "dont know", "don't know", "do not know"
        ]
        
        # Check if response matches any irrelevant pattern (in both original and normalized text)
        is_irrelevant_direct = any(pattern in text_lower for pattern in irrelevant_patterns) or \
                              any(pattern in text_normalized for pattern in irrelevant_patterns)
        
        # Also check for standalone "no" or "not" with "know" nearby
        words = text_normalized.split()
        if len(words) <= 5:  # Short responses
            if any(word in ["no", "not", "dont", "don't", "unsure"] for word in words) and \
               any(word in ["know", "idea", "clue", "sure", "remember"] for word in words):
                is_irrelevant_direct = True
        
        # Check if response is too short or just filler words
        if len(words) <= 3 and any(pattern in text_normalized for pattern in ["dont", "don't", "not", "no", "unsure"]):
            is_irrelevant_direct = True
        
        logger.info(f"🔍 Checking response for irrelevant patterns: '{text_response[:100]}...' -> is_irrelevant_direct: {is_irrelevant_direct}")
        
        # If we detected "I don't know" patterns, return early WITHOUT loading rubrics
        if is_irrelevant_direct:
            logger.info(f"❌ Direct detection: Irrelevant response detected - '{text_response[:50]}...'")
            # Return with is_irrelevant flag but NO evaluation to prevent frontend from showing feedback
            return {
                'success': True,
                'evaluation': None,  # Don't return evaluation for irrelevant responses
                'is_irrelevant': True,
                'rubric_used': False,  # Rubrics were NOT applied
                'rubric_source': None,
                'model_used': 'direct_detection',
                'message': 'Try AI Assistant for Help'
            }
        
        # Check if response is completely irrelevant to the question BEFORE loading rubrics
        # This prevents applying rubrics to irrelevant responses
        client = get_openai_client()
        relevance_check_prompt = (
            f"Question: {question}\n\n"
            f"Candidate Answer: {text_response}\n\n"
            "Determine if the candidate's answer is COMPLETELY IRRELEVANT to the question asked. "
            "An answer is completely irrelevant if it: "
            "- Does not address the question at all "
            "- Talks about something completely unrelated "
            "- Is a random response that has no connection to the question "
            "- Is gibberish or nonsensical "
            "\n"
            "Return ONLY a JSON object with this exact structure: "
            '{"is_completely_irrelevant": true/false}'
        )
        
        try:
            # Use a lightweight model for quick relevance check
            default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            relevance_completion = client.chat.completions.create(
                model=default_model,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": "You are a relevance checker. Determine if answers are completely irrelevant to questions."},
                    {"role": "user", "content": relevance_check_prompt},
                ],
                response_format={"type": "json_object"}
            )
            relevance_content = relevance_completion.choices[0].message.content
            relevance_result = json.loads(relevance_content) if isinstance(relevance_content, str) else relevance_content
            
            if isinstance(relevance_result, dict) and relevance_result.get('is_completely_irrelevant', False):
                logger.info(f"❌ Relevance check: Response is completely irrelevant to question - '{text_response[:50]}...'")
                return {
                    'success': True,
                    'evaluation': None,  # Don't return evaluation for irrelevant responses
                    'is_irrelevant': True,
                    'rubric_used': False,  # Rubrics were NOT applied
                    'rubric_source': None,
                    'model_used': 'relevance_check',
                    'message': 'Try AI Assistant for Help'
                }
        except Exception as relevance_error:
            logger.warning(f"⚠️ Relevance check failed, proceeding with rubric evaluation: {str(relevance_error)}")
            # If relevance check fails, proceed with normal evaluation
        
        # Load relaxed rubrics from Rubrics.docx for all interview types
        # Only reached if response is relevant
        rubric_text, rubric_source = load_rubric_text(skill="", interview_type=interview_type)

        prompt_system = (
            "You are an expert interview coach. Evaluate answers based on clear, specific rubrics. "
            "Be constructive, concise, and actionable. Provide a score and reasons."
        )
        
        prompt_user = (
            f"Question: {question}\n\n"
            f"Candidate Answer: {text_response}\n\n"
            f"Role: {job_title}\nSkills Context: {skills}\n\n"
            + (f"Rubric (from {rubric_source}):\n{rubric_text}\n\n" if rubric_text else "")
            + "CRITICAL: First check if the candidate answer indicates they don't know the answer. Look for phrases like: 'I don't know', 'I don't have', 'I have no idea', 'I'm not sure', 'I cannot answer', 'I don't remember', or any variation of these (including typos like 'idonot know', 'idont know', etc.). "
              "Also check if the answer is completely irrelevant to the question asked. "
              "If the answer indicates the candidate doesn't know OR is irrelevant, you MUST set 'is_irrelevant' to true and 'irrelevant_reason' to a brief explanation. "
              "ONLY if the answer is relevant and shows knowledge, evaluate it using the relaxed rubric criteria. "
              "Return JSON with fields: is_irrelevant (boolean, REQUIRED), irrelevant_reason (string, only if is_irrelevant is true), score (0-10, only if is_irrelevant is false), strengths (array of strings, only if is_irrelevant is false), improvements (array of strings, only if is_irrelevant is false), action_plan (array of 2-4 short, concrete action steps the candidate can take to improve this specific answer, only if is_irrelevant is false). "
              "Each action_plan item should be a single, specific instruction, for example: 'Add 1–2 concrete examples from your past projects.', 'Explicitly compare concept X vs Y in one sentence.', 'Practice a 60‑second version of this answer focusing only on impact and metrics.'"
        )

        client = get_openai_client()
        # Use GPT-5.2 Thinking/Pro for Skill Prep evaluation
        # Model name options: "gpt-5.2-thinking" or "gpt-5.2-pro" (configure via SKILL_PREP_MODEL env var)
        skill_prep_model = os.getenv("SKILL_PREP_MODEL", "gpt-5.2-thinking")
        default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        model_used = None
        
        try:
            # Try to use GPT-5.2 Thinking/Pro model
            completion = client.chat.completions.create(
                model=skill_prep_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user},
                ],
                response_format={"type": "json_object"}
            )
            model_used = skill_prep_model
            logger.info(f"✅ Using GPT-5.2 model ({skill_prep_model}) for Skill Prep evaluation")
            print(f"[EVALUATION] Model used: {skill_prep_model} (GPT-5.2 Thinking/Pro)")
        except Exception as model_error:
            # Fallback to default model if GPT-5.2 is not available
            logger.warning(f"⚠️ GPT-5.2 model ({skill_prep_model}) not available, falling back to {default_model}: {str(model_error)}")
            print(f"[EVALUATION] ⚠️ GPT-5.2 not available, using fallback: {default_model}")
            completion = client.chat.completions.create(
                model=default_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user},
                ],
                response_format={"type": "json_object"}
            )
            model_used = default_model
            logger.info(f"✅ Using fallback model ({default_model}) for Skill Prep evaluation")
            print(f"[EVALUATION] Model used: {default_model} (Fallback)")
        
        content = completion.choices[0].message.content
        parsed_evaluation = None
        try:
            parsed_evaluation = json.loads(content) if isinstance(content, str) else content
        except Exception:
            parsed_evaluation = content
        
        # Normalize evaluation structure and synthesize action_plan if missing
        if isinstance(parsed_evaluation, dict):
            is_irrelevant = parsed_evaluation.get('is_irrelevant', False)
            if not is_irrelevant:
                action_plan = parsed_evaluation.get('action_plan')
                # If model returned a single string, wrap it in a list
                if isinstance(action_plan, str):
                    parsed_evaluation['action_plan'] = [action_plan]
                # If no explicit action_plan, derive simple steps from improvements/summary
                elif not action_plan:
                    steps = []
                    improvements = parsed_evaluation.get('improvements') or []
                    if isinstance(improvements, list):
                        for imp in improvements:
                            if isinstance(imp, str) and imp.strip():
                                steps.append(imp.strip())
                            if len(steps) >= 4:
                                break
                    # Fallback: use summary as a single action-style step
                    summary = parsed_evaluation.get('summary')
                    if not steps and isinstance(summary, str) and summary.strip():
                        steps.append(summary.strip())
                    parsed_evaluation['action_plan'] = steps

            # Re‑serialize normalized evaluation back to JSON so frontend sees changes
            try:
                content = json.dumps(parsed_evaluation)
            except Exception:
                pass
        else:
            is_irrelevant = False
        
        # Check if response is irrelevant or "I don't know"
        
        logger.info(f"🤖 LLM evaluation result: is_irrelevant={is_irrelevant}")
        
        # If LLM detected response as completely irrelevant, don't apply rubrics and show help message
        if is_irrelevant:
            logger.info(f"❌ LLM detected: Response is irrelevant - '{text_response[:50]}...'")
            return {
                'success': True,
                'evaluation': None,  # Don't return evaluation for irrelevant responses
                'is_irrelevant': True,
                'rubric_used': False,  # Rubrics were NOT applied
                'rubric_source': None,
                'model_used': model_used,
                'message': 'Try AI Assistant for Help'
            }
        
        return {
            'success': True,
            'evaluation': content,
            'is_irrelevant': False,
            'rubric_used': bool(rubric_text),
            'rubric_source': rubric_source,
            'model_used': model_used,  # Include model name in response
        }
    except Exception as e:
        logger.error(f"Error processing text response: {e}")
        return {
            'success': False,
            'message': f'Error processing text response: {str(e)}'
        }

def process_voice_response(audio_file, question, job_title="Software Engineer", skills="Python, React", with_feedback: bool = True, interview_type: str = ""):
    """Process voice recording and return transcript with evaluation"""
    try:
        # Save uploaded file temporarily
        # Determine appropriate extension based on uploaded file metadata
        filename = getattr(audio_file, 'filename', '') or ''
        mimetype = getattr(audio_file, 'mimetype', '') or ''
        ext = '.wav'
        lower_name = filename.lower()
        if lower_name.endswith('.webm') or 'webm' in mimetype:
            ext = '.webm'
        elif lower_name.endswith('.ogg') or 'ogg' in mimetype:
            ext = '.ogg'
        elif lower_name.endswith('.mp3') or 'mp3' in mimetype:
            ext = '.mp3'
        elif lower_name.endswith('.m4a') or 'mp4' in mimetype or 'm4a' in mimetype:
            ext = '.m4a'

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            audio_file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Transcribe audio
            logger.info(f"Starting audio transcription... (ext={ext}, mimetype={mimetype})")
            transcript = transcribe_audio(temp_file_path)
            
            # Clean and validate transcript
            if transcript:
                transcript_clean = transcript.strip() if transcript else ''
                # Check if transcript is meaningful (more strict validation)
                words = transcript_clean.split() if transcript_clean else []
                word_count = len([w for w in words if re.search(r'\w', w)])
                
                is_meaningful = (
                    len(transcript_clean) >= 10 and  # At least 10 characters
                    word_count >= 2 and  # At least 2 words
                    bool(re.search(r'\w', transcript_clean)) and  # Contains word characters
                    not re.match(r'^(uh+|um+|er+|ah+|hmm+|\.{2,}|\s+|[\.\s\-_]+)$', transcript_clean, re.IGNORECASE) and
                    not re.match(r'^[^\w\s]+$', transcript_clean)  # Not just punctuation
                )
                
                if is_meaningful:
                    logger.info(f"Transcription successful: {transcript_clean[:100]}...")
                    if with_feedback:
                        eval_result = process_text_response(transcript_clean, question, job_title=job_title, skills=skills, interview_type=interview_type)
                    else:
                        eval_result = None
                    return {
                        'success': True,
                        'transcript': transcript_clean,
                        'question': question,
                        'message': 'Voice response processed successfully',
                        'evaluation': (eval_result.get('evaluation') if eval_result and eval_result.get('success') else None),
                        'is_irrelevant': (eval_result.get('is_irrelevant') if eval_result and eval_result.get('success') else False),
                        'rubric_used': (eval_result.get('rubric_used') if eval_result else False),
                        'rubric_source': (eval_result.get('rubric_source') if eval_result else None),
                        'model_used': (eval_result.get('model_used') if eval_result else None),  # Include model name
                    }
                else:
                    logger.warning(f"Transcript detected but not meaningful: '{transcript_clean}' (length: {len(transcript_clean)})")
                    return {
                        'success': False,
                        'message': 'No meaningful speech detected. Please try again.',
                        'transcript': transcript_clean  # Include for debugging
                    }
            else:
                logger.error("Transcription failed - no transcript returned")
                return {
                    'success': False,
                    'message': 'Failed to transcribe audio. Please try again.'
                }
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logger.error(f"Error processing voice response: {e}")
        return {
            'success': False,
            'message': f'Server error during voice processing: {str(e)}'
        }

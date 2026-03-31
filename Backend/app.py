from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_session import Session
import psycopg2
from psycopg2 import sql
from db_handler import get_pg_connection, create_users_table, drop_dashboard_tables
from auth import auth_bp, api_login_required
import os
from dotenv import load_dotenv
import json
import re
import difflib
import logging
import traceback
import random
from voice_processor import process_text_response, get_openai_client
from mock_interview.session_manager import session_manager as iqra_session_manager
from mock_interview.agents import (
    QuestionAgent as IqraQuestionAgent,
    EvaluatorAgent as IqraEvaluatorAgent,
    FollowUpAgent as IqraFollowUpAgent,
    HintAgent as IqraHintAgent,
    RecruiterAgent as IqraRecruiterAgent,
    IntentDetectorAgent as IqraIntentDetectorAgent,
    ImprovementAgent as IqraImprovementAgent,
)
from mock_interview.config import JOB_ROLE_SKILLS as IQRA_JOB_ROLE_SKILLS, INTERVIEW_TYPES as IQRA_INTERVIEW_TYPES
from rubric_loader import load_rubric_text
from random import shuffle
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for dynamic keywords extracted from question tables
_DB_KEYWORDS_CACHE = {"keywords": [], "updated_at": None}
_DB_KEYWORDS_TTL_SECONDS = 600

_KEYWORD_STOPWORDS = {
    'the', 'and', 'for', 'with', 'that', 'this', 'these', 'those', 'from', 'into',
    'what', 'why', 'how', 'when', 'where', 'which', 'who', 'whom', 'can', 'could',
    'should', 'would', 'will', 'shall', 'may', 'might', 'must', 'about', 'explain',
    'describe', 'define', 'difference', 'between', 'use', 'using', 'used', 'like',
    'your', 'you', 'are', 'is', 'was', 'were', 'be', 'been', 'being', 'do', 'does',
    'did', 'a', 'an', 'in', 'on', 'at', 'to', 'of', 'or', 'as', 'by', 'it', 'its'
}

def execute_db_query(query, params=None, fetch_one=False, fetch_all=False):
    """Utility function to execute database queries and reduce code duplication."""
    try:
        conn = get_pg_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            
            if fetch_one:
                return cursor.fetchone(), None
            elif fetch_all:
                return cursor.fetchall(), None
            else:
                conn.commit()
                return True, None
                
    except Exception as e:
        return None, str(e)
    finally:
        if 'conn' in locals():
            conn.close()

app = Flask(__name__)
load_dotenv()

# Platform skills (sync with frontend/src/jobRolesConfig.js)
PLATFORM_SKILLS = {
    'AI Engineer': ['Machine Learning', 'Python', 'TensorFlow', 'PyTorch', 'Deep Learning'],
    'Data Scientist': ['Python', 'Machine Learning', 'SQL', 'Data Analysis', 'Statistics'],
    'Python Developer': ['Python', 'AWS', 'Kubernetes', 'Docker', 'Lambda'],
    'Machine Learning Engineer': ['Python', 'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch'],
    'MLOps Engineer': ['AWS', 'Docker', 'Kubernetes', 'Machine Learning', 'Python'],
    'Data Engineer': ['Python', 'SQL', 'AWS', 'Lambda', 'Docker'],
    'Deep Learning Engineer': ['Python', 'Deep Learning', 'TensorFlow', 'PyTorch', 'AWS'],
    'Cloud AI Engineer': ['AWS', 'Lambda', 'Machine Learning', 'Docker', 'Python'],
    'Backend Engineer (AI/ML Focused)': ['Python', 'SQL', 'AWS', 'Docker', 'Machine Learning'],
}


# Interview Type Configuration - Using relaxed rubrics from Rubrics.docx for all types
# Rubrics are now loaded dynamically from the docx file
INTERVIEW_TYPE_CONFIG = {
    'behavioral': {
        'rubric_dimensions': {
            'relevance': {'weight': 0.40, 'label': 'Relevance'},
            'completeness': {'weight': 0.25, 'label': 'Completeness'},
            'communication_clarity': {'weight': 0.20, 'label': 'Clarity'},
            'accuracy': {'weight': 0.15, 'label': 'Accuracy'}
        },
        'score_formula': 'Overall Score = (Relevance × 0.40) + (Completeness × 0.25) + (Clarity × 0.20) + (Accuracy × 0.15)',
        'dimensions_text': """
   For Behavioral Interviews:
   - Relevance (0-10, Weight: 40%)
   - Completeness (0-10, Weight: 25%)
   - Clarity (0-10, Weight: 20%)
   - Accuracy (0-10, Weight: 15%)

2. Calculate the weighted overall score:
   Overall Score = (Relevance × 0.40) + (Completeness × 0.25) + (Clarity × 0.20) + (Accuracy × 0.15)""",
        'default_rubrics': None  # Will be loaded from Rubrics.docx
    },
    'default': {
        'rubric_dimensions': {
            'relevance': {'weight': 0.40, 'label': 'Relevance'},
            'completeness': {'weight': 0.25, 'label': 'Completeness'},
            'communication_clarity': {'weight': 0.20, 'label': 'Clarity'},
            'accuracy': {'weight': 0.15, 'label': 'Accuracy'}
        },
        'score_formula': 'Overall Score = (Relevance × 0.40) + (Completeness × 0.25) + (Clarity × 0.20) + (Accuracy × 0.15)',
        'dimensions_text': """
   For Technical/Other Interviews:
   - Relevance (0-10, Weight: 40%)
   - Completeness (0-10, Weight: 25%)
   - Clarity (0-10, Weight: 20%)
   - Accuracy (0-10, Weight: 15%)

2. Calculate the weighted overall score:
   Overall Score = (Relevance × 0.40) + (Completeness × 0.25) + (Clarity × 0.20) + (Accuracy × 0.15)""",
        'default_rubrics': None  # Will be loaded from Rubrics.docx
    }
}

def get_interview_config(interview_type):
    """Get interview configuration based on type - dictionary lookup (no if-else)"""
    normalized_type = interview_type.lower() if interview_type else 'default'
    return INTERVIEW_TYPE_CONFIG.get(normalized_type, INTERVIEW_TYPE_CONFIG['default'])

def get_question_table_name(interview_type, skill=''):
    """Get question table name based on interview type and skill - dictionary-based (no if-else)"""
    normalized_type = interview_type.lower() if interview_type else 'default'
    table_config = {'behavioral': 'behavioralquestions'}
    return table_config.get(normalized_type, f"{interview_type}_{skill.lower().replace(' ', '')}")

def get_interview_type_label(interview_type):
    """Get interview type label - dictionary-based (no if-else)"""
    label_map = {'behavioral': 'behavioral interview', 'default': 'interview'}
    normalized_type = interview_type.lower() if interview_type else 'default'
    return label_map.get(normalized_type, label_map['default'])

def calculate_weighted_score(rubric_scores, interview_type):
    """Calculate weighted overall score based on interview type - dictionary-based (no if-else)"""
    config = get_interview_config(interview_type)
    dimensions = config['rubric_dimensions']
    
    total_score = 0.0
    for dimension_key, dimension_info in dimensions.items():
        score = rubric_scores.get(dimension_key, {}).get('score', 0)
        weight = dimension_info['weight']
        total_score += score * weight
    
    return round(total_score, 2)

def generate_feedback_prompt_json_structure(interview_type):
    """Generate JSON structure for feedback prompt based on interview type - dictionary-based (no if-else)"""
    config = get_interview_config(interview_type)
    dimensions = config['rubric_dimensions']
    
    rubric_scores_json = "{\n"
    for idx, (dimension_key, dimension_info) in enumerate(dimensions.items()):
        weight = dimension_info['weight']
        rubric_scores_json += f'    "{dimension_key}": {{\n'
        rubric_scores_json += f'      "score": <0-10>,\n'
        rubric_scores_json += f'      "weight": {weight},\n'
        rubric_scores_json += f'      "strengths": ["strength1", "strength2"],\n'
        rubric_scores_json += f'      "improvements": ["improvement1", "improvement2"],\n'
        rubric_scores_json += f'      "evidence": "specific examples from conversation"\n'
        rubric_scores_json += f'    }}'
        rubric_scores_json += ",\n" if idx < len(dimensions) - 1 else "\n"
    rubric_scores_json += "  }"
    
    return rubric_scores_json

def generate_feedback_prompt(interview_type, candidate_name, user_messages_count):
    """Generate feedback prompt based on interview type - dictionary-based (no if-else)"""
    config = get_interview_config(interview_type)
    rubric_json = generate_feedback_prompt_json_structure(interview_type)
    
    interview_type_label = get_interview_type_label(interview_type)
    dimension_names = ", ".join([info['label'].lower() for info in config['rubric_dimensions'].values()])
    
    # Load rubrics from docx file
    rubric_text, rubric_source = load_rubric_text(skill="", interview_type=interview_type)
    rubric_section = ""
    if rubric_text:
        rubric_section = f"\n\nEVALUATION RUBRICS (from {rubric_source}):\n{rubric_text}\n"
    
    prompt = f"""Based on the conversation history provided above, please provide comprehensive, rubric-based feedback for {candidate_name}'s {interview_type_label} performance.

CRITICAL: 
- Evaluate ONLY based on the actual conversation history shown above
- If the candidate did not answer questions, provided minimal responses, or the interview was incomplete, reflect this in scores and feedback
- Base all scores on specific evidence from the conversation - if there's no evidence, provide lower scores
- If conversation is insufficient (less than {user_messages_count} candidate responses), provide appropriate feedback indicating the interview was incomplete
- Use the relaxed rubrics provided below - be fair and understanding in evaluation
{rubric_section}
REQUIRED OUTPUT FORMAT (JSON):
{{
  "overall_score": <weighted score out of 10>,
  "rubric_scores": {{
{rubric_json}
  }},
  "summary": "Write a comprehensive overall feedback that COMBINES all rubric aspects ({dimension_names}) into ONE unified narrative. Mention what was good and what needs improvement, but DO NOT mention these rubric dimensions by name. Write naturally as if giving overall {interview_type_label} feedback.",
  "key_strengths": ["combined strength mentioning all good aspects", "another combined strength", "third combined strength"],
  "areas_for_improvement": ["combined area mentioning what needs work", "another combined area", "third combined area"],
  "recommendations": ["recommendation1", "recommendation2", "recommendation3"]
}}

CRITICAL INSTRUCTIONS: 
- Calculate overall_score using the weighted formula: {config['score_formula']}
- Base all scores on the relaxed rubric criteria provided above
- The rubric_scores are for INTERNAL USE ONLY - they will not be displayed to the candidate
- The "summary" field MUST be ONE unified overall feedback - DO NOT mention individual rubric dimensions as separate things
- DO NOT use phrases like "in terms of", "regarding", "with respect to" followed by rubric dimension names
- Instead, write naturally combining all aspects
- Key strengths should be COMBINED - don't separate by rubric dimensions
- Areas for improvement should be COMBINED - don't separate by rubric dimensions
- Be fair, understanding, and use the relaxed evaluation standards from the rubrics"""
    
    return prompt

# Configure Flask session
secret_key = os.getenv('SECRET_KEY')
is_debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
frontend_url_env = os.getenv('FRONTEND_URL', '').strip().rstrip('/')
is_remote_frontend = (
    frontend_url_env.startswith('https://')
    and 'localhost' not in frontend_url_env
    and '127.0.0.1' not in frontend_url_env
)
is_production = any(
    (
        os.getenv('FLASK_ENV', '').lower() == 'production',
        os.getenv('ENV', '').lower() == 'production',
        os.getenv('APP_ENV', '').lower() == 'production',
        os.getenv('RENDER', '').lower() == 'true',
        bool(os.getenv('RENDER_SERVICE_ID')),
        is_remote_frontend,
    )
)
if not secret_key:
    if is_production:
        raise RuntimeError("SECRET_KEY is required in production")
    secret_key = 'dev-secret-key'
    logger.warning("SECRET_KEY not set; using dev-only key")

app.config['SECRET_KEY'] = secret_key
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'practice2panel:'
app.config['PERMANENT_SESSION_LIFETIME'] = 2592000  # 30 days in seconds

# Session cookie settings for OAuth (important for state parameter)
app.config['SESSION_COOKIE_HTTPONLY'] = True

# For production (Render + Vercel: different domains, HTTPS), we must use
# SameSite=None and Secure=True so cookies are sent on cross-site XHR.
if is_production:
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_SECURE'] = True
else:
    # Local development: allow http and typical browser defaults
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False

app.config['SESSION_COOKIE_DOMAIN'] = None  # Don't restrict domain - allows localhost and 127.0.0.1
app.config['SESSION_COOKIE_PATH'] = '/'  # Make sure cookies are available for all paths

# Initialize Flask-Session
Session(app)

# Enable CORS for frontend communication with credentials support
# IMPORTANT: Cannot use "*" with supports_credentials=True - must specify exact origins
# FRONTEND_URL + optional CORS_ORIGINS — see cors_config.py
from cors_config import get_allowed_origins, is_origin_allowed, get_vercel_origin_pattern

allowed_origins = get_allowed_origins()
vercel_origin_pattern = get_vercel_origin_pattern()


def _flask_cors_origins():
    """Exact URLs from env plus optional Vercel preview regex (see cors_config)."""
    out = list(allowed_origins)
    if vercel_origin_pattern:
        out.append(vercel_origin_pattern)
    return out


# Apply CORS globally to all routes (more reliable than resource-specific)
CORS(app, 
     supports_credentials=True, 
     origins=_flask_cors_origins(),
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
     expose_headers=["Set-Cookie"])

# Helper function for CORS OPTIONS responses
def create_cors_options_response(methods="GET, POST, PUT, DELETE, OPTIONS"):
    """Create a standardized CORS OPTIONS response."""
    origin = request.headers.get('Origin')
    if not origin or not is_origin_allowed(origin, allowed_origins, vercel_origin_pattern):
        return jsonify({'success': False, 'message': 'CORS origin not allowed'}), 403
    # Echo the browser's Origin header exactly as sent (required for credentialed CORS).
    response = jsonify({'success': True})
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Headers'] = (
        'Content-Type, Authorization, Accept, Origin, X-Requested-With'
    )
    response.headers['Access-Control-Allow-Methods'] = methods
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response, 200

# Global CORS handler for all OPTIONS requests
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return create_cors_options_response()

# Add CORS headers to ALL responses (including errors)
# Only add if not already present (to avoid duplicates with global CORS)
@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses if not already present"""
    # Check if CORS headers already exist (from global CORS config)
    if 'Access-Control-Allow-Origin' not in response.headers:
        origin = request.headers.get('Origin')
        if origin and is_origin_allowed(origin, allowed_origins, vercel_origin_pattern):
            response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = (
            'Content-Type, Authorization, Accept, Origin, X-Requested-With'
        )

    return response

# Register auth blueprint
app.register_blueprint(auth_bp)

# Error handler to ensure CORS headers on all errors
@app.errorhandler(500)
def handle_500_error(e):
    """Handle 500 errors with CORS headers"""
    # Safely encode error message
    try:
        error_msg = str(e)
        error_msg = error_msg.encode('ascii', 'replace').decode('ascii')
    except:
        error_msg = "Internal server error"
    
    response = jsonify({
        'success': False,
        'message': f'Server error: {error_msg}'
    })
    
    origin = request.headers.get('Origin')
    if origin and is_origin_allowed(origin, allowed_origins, vercel_origin_pattern):
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = (
        'Content-Type, Authorization, Accept, Origin, X-Requested-With'
    )
    return response, 500

# Initialize users table on startup (database is optional for basic usage)
try:
    create_users_table()
    print("Users table initialized")
except Exception as e:
    # Avoid non-ASCII symbols here to prevent UnicodeEncodeError on some Windows consoles
    print(f"Warning: Failed to initialize users table: {e}")

# Drop dashboard tables if they exist (dashboard removed)
try:
    drop_dashboard_tables()
    print("Dashboard tables removed")
except Exception as e:
    print(f"Warning: Failed to remove dashboard tables: {e}")



def get_questions_from_table(table_name):
    """Fetch questions from database table by table name (case-insensitive)"""
    try:
        # Check if table exists (case-insensitive check)
        table_check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE LOWER(table_name) = LOWER(%s)
            );
        """
        
        result, error = execute_db_query(table_check_query, (table_name,), fetch_one=True)
        if error:
            logger.error(f"Error checking table existence for {table_name}: {error}")
            return None, error
        
        if not result or not result[0]:
            logger.warning(f"Table {table_name} does not exist in database")
            return None, f"Table '{table_name}' does not exist"
        
        # Get the actual table name from database (case-sensitive)
        get_table_name_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE LOWER(table_name) = LOWER(%s)
            LIMIT 1;
        """
        table_result, error = execute_db_query(get_table_name_query, (table_name,), fetch_one=True)
        if error or not table_result:
            logger.error(f"Error getting actual table name for {table_name}: {error}")
            return None, f"Could not find table '{table_name}'"
        
        actual_table_name = table_result[0]
        logger.info(f"Found table: {actual_table_name} (requested: {table_name})")
        
        # Fetch questions from the table
        query = sql.SQL("SELECT question FROM {} ORDER BY id").format(sql.Identifier(actual_table_name))
        questions_result, error = execute_db_query(query, fetch_all=True)
        
        if error:
            logger.error(f"Error fetching questions from {actual_table_name}: {error}")
            return None, error
        
        questions = [row[0] for row in questions_result] if questions_result else []
        logger.info(f"Fetched {len(questions)} questions from table {actual_table_name}")
        return questions, None
        
    except Exception as e:
        logger.error(f"Exception in get_questions_from_table for {table_name}: {str(e)}")
        return None, f"Error fetching questions: {str(e)}"

def get_question_with_reference(table_name, question_text):
    """Fetch question with its reference answer from database table"""
    # Check if table exists
    table_check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        );
    """
    
    result, error = execute_db_query(table_check_query, (table_name,), fetch_one=True)
    if error:
        return None, error
    
    table_exists = result[0]
    if not table_exists:
        return None, "Table does not exist"
    
    # First try exact match
    query = sql.SQL("SELECT question, explanation FROM {} WHERE question = %s").format(sql.Identifier(table_name))
    result, error = execute_db_query(query, (question_text,), fetch_one=True)
    
    if error:
        return None, error
    
    if result:
        return {
            'question': result[0],
            'reference_answer': result[1] or "No reference answer available"
        }, None
    
    # If exact match fails, try partial match (remove numbers and extra spaces)
    clean_question = question_text.strip()
    # Remove leading numbers and dots (e.g., "1. " or "2. ")
    clean_question = re.sub(r'^\d+\.\s*', '', clean_question)
    
    # Try partial match using ILIKE for case-insensitive search
    query = sql.SQL("SELECT question, explanation FROM {} WHERE question ILIKE %s").format(sql.Identifier(table_name))
    result, error = execute_db_query(query, (f'%{clean_question}%',), fetch_one=True)
    
    if error:
        return None, error
    
    if result:
        return {
            'question': result[0],
            'reference_answer': result[1] or "No reference answer available"
        }, None
    
    # If still no match, try to find any question that contains the main keywords
    keywords = clean_question.split()[:3]  # Take first 3 words as keywords
    if keywords:
        keyword_pattern = '%'.join(keywords)
        query = sql.SQL("SELECT question, explanation FROM {} WHERE question ILIKE %s LIMIT 1").format(sql.Identifier(table_name))
        result, error = execute_db_query(query, (f'%{keyword_pattern}%',), fetch_one=True)
        
        if error:
            return None, error
        
        if result:
            return {
                'question': result[0],
                'reference_answer': result[1] or "No reference answer available"
            }, None
    
    return None, "Question not found"

@app.route('/api/questions/<interview_type>/<skill>', methods=['GET'])
def get_questions(interview_type, skill):
    """Get questions for a specific interview type and skill"""
    try:
        # Get table name based on interview type (dictionary-based, no if-else)
        table_name = get_question_table_name(interview_type, skill)
        
        questions, error = get_questions_from_table(table_name)
        
        if error:
            if "Table does not exist" in error:
                return jsonify({
                    'success': False,
                    'message': 'UnAvailable Questions',
                    'questions': []
                }), 404
            else:
                return jsonify({
                    'success': False,
                    'message': f'Database error: {error}',
                    'questions': []
                }), 500
        
        if not questions:
            return jsonify({
                'success': False,
                'message': 'UnAvailable Questions',
                'questions': []
            }), 404
        
        return jsonify({
            'success': True,
            'message': f'Found {len(questions)} questions',
            'questions': questions
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}',
            'questions': []
        }), 500


# Evaluation endpoints removed per requirements

@app.route('/api/process-voice', methods=['POST'])
def process_voice():
    """Process voice recording and return transcript"""
    try:
        from voice_processor import process_voice_response
        
        # Check if audio file is present
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No audio file provided'
            }), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No audio file selected'
            }), 400
        
        # Get question from form data
        question = request.form.get('question', 'Practice question')
        
        # Process the voice response
        result = process_voice_response(audio_file, question)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error during voice processing: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'API is running',
        'status': 'healthy'
    })


def _iqra_handle_next_main_question(session, session_id):
    """Advance to the next main question for the Iqra mock interview flow."""
    session.current_question_index += 1

    if session.current_question_index < len(session.questions):
        next_question = session.questions[session.current_question_index]
        session.last_question = next_question
        return jsonify({
            "message": IqraRecruiterAgent.get_polite_message("next"),
            "next_question": next_question,
            "is_followup": False,
            "session_id": session_id,
            "intent": "normal_answer",
            "question_number": session.current_question_index + 1,
            "total_questions": len(session.questions)
        }), 200

    session.completed = True
    return jsonify({
        "message": IqraRecruiterAgent.get_polite_message("complete"),
        "completed": True,
        "session_id": session_id,
        "intent": "normal_answer"
    }), 200


@app.route('/api/mock-interview/start', methods=['POST'])
def iqra_start_interview():
    """Start a new mock interview session (Iqra flow)."""
    try:
        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        job_role = (data.get('job_role') or '').strip()
        interview_type = (data.get('interview_type') or '').strip()

        if not name:
            return jsonify({"error": "Name is required"}), 400
        if job_role not in PLATFORM_SKILLS:
            return jsonify({"error": f"Invalid job role. Must be one of: {list(PLATFORM_SKILLS.keys())}"}), 400
        if interview_type not in IQRA_INTERVIEW_TYPES:
            return jsonify({"error": f"Invalid interview type. Must be one of: {IQRA_INTERVIEW_TYPES}"}), 400

        session_obj = iqra_session_manager.create_session(name, job_role, interview_type)

        skills = PLATFORM_SKILLS.get(job_role, [])
        questions = []
        normalized_type = interview_type.lower() if interview_type else ''

        if normalized_type == "behavioral":
            table_name = get_question_table_name(interview_type)
            table_questions, error = get_questions_from_table(table_name)
            if table_questions:
                random.shuffle(table_questions)
                questions = table_questions[:min(10, len(table_questions))]
        else:
            for skill in skills:
                table_name = get_question_table_name(interview_type, skill)
                table_questions, error = get_questions_from_table(table_name)
                if table_questions:
                    random.shuffle(table_questions)
                    pick_count = random.randint(3, 4)
                    pick_count = min(pick_count, len(table_questions))
                    questions.extend(table_questions[:pick_count])

        if not questions:
            questions = IqraQuestionAgent.generate_questions(job_role, interview_type, num_questions=5)

        random.shuffle(questions)
        session_obj.questions = questions

        if questions:
            session_obj.current_question_index = 0
            session_obj.last_question = questions[0]

        welcome_message = None
        if interview_type.lower() == "behavioral":
            welcome_message = IqraRecruiterAgent.get_welcome_message(name, interview_type)

        response_data = {
            "session_id": session_obj.session_id,
            "name": session_obj.name,
            "job_role": session_obj.job_role,
            "interview_type": session_obj.interview_type,
            "first_question": questions[0] if questions else "No questions generated",
            "total_questions": len(questions),
        }
        if welcome_message:
            response_data["welcome_message"] = welcome_message

        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/mock-interview/interact', methods=['POST'])
def iqra_interact():
    """Handle mock interview interactions with automatic intent detection."""
    try:
        data = request.get_json() or {}
        session_id = (data.get('session_id') or '').strip()
        user_input = (data.get('user_input') or '').strip()

        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        if not user_input:
            return jsonify({"error": "user_input is required"}), 400

        session_obj = iqra_session_manager.get_session(session_id)
        if not session_obj:
            return jsonify({"error": "Invalid session_id"}), 404

        current_question = session_obj.last_question or ""
        if session_obj.current_question_index < len(session_obj.questions) and not current_question:
            current_question = session_obj.questions[session_obj.current_question_index]

        try:
            intent = IqraIntentDetectorAgent.detect_intent(
                user_input=user_input,
                current_question=current_question,
                conversation_state=""
            )
        except Exception as e:
            logger.warning(f"Iqra intent detection error: {e}")
            intent = "normal_answer"

        if intent == 'repeat_question':
            return jsonify({
                "message": IqraRecruiterAgent.get_polite_message("repeat"),
                "question": session_obj.last_question,
                "session_id": session_id,
                "intent": "repeat_question"
            }), 200

        if intent == 'hint_request':
            if not session_obj.last_question:
                return jsonify({"error": "No question available for hint"}), 400

            hint = IqraHintAgent.provide_hint(
                session_obj.last_question,
                session_obj.job_role,
                session_obj.interview_type
            )
            return jsonify({
                "hint": hint,
                "message": "Here's a hint to help guide your thinking:",
                "session_id": session_id,
                "intent": "hint_request"
            }), 200

        if intent == 'need_time':
            return jsonify({
                "message": IqraRecruiterAgent.get_polite_message("pause"),
                "session_id": session_id,
                "intent": "need_time",
                "pause_seconds": 10
            }), 200

        if intent == 'normal_answer':
            is_followup = session_obj.current_follow_up_index < len(session_obj.follow_up_questions)

            if is_followup:
                current_followup = session_obj.follow_up_questions[session_obj.current_follow_up_index]
                evaluation = IqraEvaluatorAgent.evaluate_answer(
                    current_followup,
                    user_input,
                    session_obj.job_role,
                    session_obj.interview_type
                )

                session_obj.answers.append({
                    "question": current_followup,
                    "answer": user_input,
                    "is_followup": True,
                    "parent_question_index": session_obj.current_question_index - 1,
                    "feedback": evaluation["short_feedback"],
                    "detailed_evaluation": evaluation["detailed_evaluation"]
                })
                session_obj.detailed_evaluations.append({
                    "question": current_followup,
                    "evaluation": evaluation
                })

                session_obj.current_follow_up_index += 1

                if session_obj.current_follow_up_index < len(session_obj.follow_up_questions):
                    next_followup = session_obj.follow_up_questions[session_obj.current_follow_up_index]
                    session_obj.last_question = next_followup
                    return jsonify({
                        "feedback": evaluation["short_feedback"],
                        "next_question": next_followup,
                        "is_followup": True,
                        "session_id": session_id,
                        "intent": "normal_answer"
                    }), 200

                session_obj.follow_up_questions = []
                session_obj.current_follow_up_index = 0
                return _iqra_handle_next_main_question(session_obj, session_id)

            if session_obj.current_question_index >= len(session_obj.questions):
                return jsonify({"error": "No more questions available"}), 400
            current_question = session_obj.questions[session_obj.current_question_index]
            evaluation = IqraEvaluatorAgent.evaluate_answer(
                current_question,
                user_input,
                session_obj.job_role,
                session_obj.interview_type
            )

            session_obj.answers.append({
                "question": current_question,
                "answer": user_input,
                "is_followup": False,
                "feedback": evaluation["short_feedback"],
                "detailed_evaluation": evaluation["detailed_evaluation"]
            })
            session_obj.detailed_evaluations.append({
                "question": current_question,
                "evaluation": evaluation
            })

            follow_ups = IqraFollowUpAgent.generate_follow_ups(
                current_question,
                user_input,
                session_obj.job_role,
                session_obj.interview_type
            )

            if follow_ups:
                session_obj.follow_up_questions = [follow_ups[0]]
                session_obj.current_follow_up_index = 0
                session_obj.last_question = follow_ups[0]

                return jsonify({
                    "feedback": evaluation["short_feedback"],
                    "follow_up_question": follow_ups[0],
                    "is_followup": True,
                    "session_id": session_id,
                    "intent": "normal_answer"
                }), 200

            return _iqra_handle_next_main_question(session_obj, session_id)

        return jsonify({
            "error": "Unable to determine intent, please try again",
            "session_id": session_id
        }), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/mock-interview/end', methods=['POST'])
def iqra_end_interview():
    """End interview and return detailed summary (Iqra flow)."""
    try:
        data = request.get_json() or {}
        session_id = (data.get('session_id') or '').strip()

        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        session_obj = iqra_session_manager.get_session(session_id)
        if not session_obj:
            return jsonify({"error": "Invalid session_id"}), 404

        if session_obj.interview_type.lower() == "behavioral":
            all_scores = {
                "Situation Clarity": [],
                "Task Definition": [],
                "Action Effectiveness": [],
                "Result Impact": [],
                "Communication Skill": []
            }
        else:
            all_scores = {
                "Technical Accuracy": [],
                "Clarity of Communication": [],
                "Depth of Understanding": [],
                "Relevance to Role": [],
                "Overall Quality": []
            }

        for eval_data in session_obj.detailed_evaluations:
            evaluation = eval_data.get("evaluation", {})
            rubric = evaluation.get("rubric_scores", {})
            for metric in all_scores.keys():
                if metric in rubric:
                    score_str = rubric[metric]
                    try:
                        score = float(score_str.split('/')[0].strip())
                        all_scores[metric].append(score)
                    except Exception:
                        pass

        overall_scores = {}
        for metric, scores in all_scores.items():
            if scores:
                avg_score = round(sum(scores) / len(scores), 1)
                overall_scores[metric] = f"Score: {avg_score}/10"
            else:
                overall_scores[metric] = "Score: 0/10"

        improvements = IqraImprovementAgent.generate_improvements(
            session_obj.detailed_evaluations,
            session_obj.job_role,
            session_obj.interview_type
        )

        closing_message = IqraRecruiterAgent.get_closing_message(
            session_obj.name,
            session_obj.interview_type,
            overall_scores
        )

        summary = {
            "session_id": session_id,
            "name": session_obj.name,
            "job_role": session_obj.job_role,
            "interview_type": session_obj.interview_type,
            "total_questions": len(session_obj.questions),
            "total_answers": len(session_obj.answers),
            "overall_scores": overall_scores,
            "areas_of_improvement": improvements,
            "closing_message": closing_message
        }

        session_obj.completed = True
        return jsonify(summary), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/mock-interview/next-question', methods=['POST'])
def iqra_next_question():
    """Advance to the next main question explicitly (Iqra flow)."""
    try:
        data = request.get_json() or {}
        session_id = (data.get('session_id') or '').strip()
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        session_obj = iqra_session_manager.get_session(session_id)
        if not session_obj:
            return jsonify({"error": "Invalid session_id"}), 404

        session_obj.follow_up_questions = []
        session_obj.current_follow_up_index = 0

        return _iqra_handle_next_main_question(session_obj, session_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _build_dashboard_filters(interview_type=None, skill=None):
    conditions = ["user_id = %s"]
    params = [session.get('user_id')]
    if interview_type:
        conditions.append("LOWER(interview_type) = LOWER(%s)")
        params.append(interview_type)
    if skill:
        conditions.append("LOWER(skill) = LOWER(%s)")
        params.append(skill)
    where_clause = " AND ".join(conditions)
    return where_clause, params

# @app.route('/api/dashboard/summary', methods=['GET'])
@api_login_required
def dashboard_summary():
    """Return dashboard summary with filters and charts data."""
    try:
        interview_type = request.args.get('interview_type') or None
        skill = request.args.get('skill') or None
        where_clause, params = _build_dashboard_filters(interview_type, skill)

        conn = get_pg_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*), COALESCE(SUM(duration_seconds), 0)
                    FROM skill_prep_questions
                    WHERE user_id = %s
                    """,
                    (session.get('user_id'),)
                )
                questions_total, questions_time_seconds = cursor.fetchone()

                cursor.execute(
                    f"""
                    SELECT interview_type, skill, COUNT(*)
                    FROM skill_prep_questions
                    WHERE {where_clause}
                    GROUP BY interview_type, skill
                    ORDER BY interview_type, skill
                    """,
                    params
                )
                questions_breakdown = [
                    {'interview_type': row[0], 'skill': row[1], 'count': int(row[2])}
                    for row in cursor.fetchall()
                ]

                cursor.execute(
                    """
                    SELECT interview_type, skill, last_question_index, total_questions, last_question_text, updated_at
                    FROM skill_prep_progress
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 10
                    """,
                    (session.get('user_id'),)
                )
                skill_progress = [
                    {
                        'interview_type': row[0],
                        'skill': row[1],
                        'last_question_index': int(row[2] or 0),
                        'total_questions': int(row[3] or 0),
                        'last_question_text': row[4],
                        'updated_at': row[5].isoformat()
                    }
                    for row in cursor.fetchall()
                ]
                cursor.execute(
                    f"""
                    SELECT interview_type, skill, question_index, question_text, duration_seconds, created_at
                    FROM skill_prep_questions
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT 15
                    """,
                    params
                )
                recent_questions = [
                    {
                        'interview_type': row[0],
                        'skill': row[1],
                        'question_index': int(row[2]) if row[2] is not None else None,
                        'question_text': row[3],
                        'duration_seconds': int(row[4] or 0),
                        'created_at': row[5].isoformat()
                    }
                    for row in cursor.fetchall()
                ]

            summary = {
                'questions_total': int(questions_total or 0),
                'questions_time_seconds': int(questions_time_seconds or 0),
                'questions_breakdown': questions_breakdown,
                'skill_progress': skill_progress,
                'recent_questions': list(reversed(recent_questions))
            }

            return jsonify({'success': True, 'summary': summary}), 200
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error loading dashboard summary: {str(e)}'}), 500


def format_relative_time(dt_value):
    """Format datetime as relative time (e.g., '2 days ago')."""
    if not dt_value:
        return 'N/A'
    now = datetime.utcnow()
    if dt_value.tzinfo is not None:
        dt_value = dt_value.replace(tzinfo=None)
    delta = now - dt_value
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return 'Just now'
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hr ago"
    days = hours // 24
    if days < 7:
        return f"{days} days ago"
    weeks = days // 7
    if weeks < 4:
        return f"{weeks} weeks ago"
    months = days // 30
    if months < 12:
        return f"{months} months ago"
    years = days // 365
    return f"{years} years ago"


def build_context_info(context):
    """Build context information string from context dict."""
    context_info = ""
    interview_type = context.get('interviewType')
    if context.get('currentQuestion'):
        context_info += f"\n\nCurrent Question Being Practiced: {context['currentQuestion']}"
    if context.get('skill'):
        context_info += f"\nSkill Area: {context['skill']}"
    if context.get('role'):
        context_info += f"\nTarget Role: {context['role']}"
    if interview_type:
        context_info += f"\nInterview Type: {interview_type}"

    # Include rubric overview to allow rubric-based explanations
    config = get_interview_config(interview_type)
    rubric_lines = []
    for key, info in config['rubric_dimensions'].items():
        rubric_lines.append(f"- {info['label']}: {int(info['weight'] * 100)}%")
    rubric_text = "\n".join(rubric_lines)
    context_info += f"\nRubric Basis (use this when user asks about evaluation):\n{rubric_text}"

    # Include platform skills for interview tips scope
    skills_lines = []
    for role, skills in PLATFORM_SKILLS.items():
        skills_lines.append(f"- {role}: {', '.join(skills)}")
    context_info += "\nPlatform Skills (answer tips within these skills):\n" + "\n".join(skills_lines)
    return context_info

def is_rubric_question(message):
    """Detect if the user is asking about evaluation basis or rubric."""
    if not message:
        return False
    text = message.lower()
    rubric_keywords = [
        'rubric', 'criteria', 'basis', 'evaluate', 'evaluation',
        'assessment', 'score', 'marks', 'grading', 'measure',
        'kis basis', 'kis baisis', 'kis criteria', 'evaluate ho',
        'evaluation kis', 'rubrics', 'rebics', 'rubics'
    ]
    return any(keyword in text for keyword in rubric_keywords)

def is_behavioral_mention(message):
    """Detect behavioral interview mentions including common misspellings."""
    if not message:
        return False
    text = message.lower()
    behavioral_variants = [
        'behavioral', 'behavioural', 'behvirla', 'behviral', 'behverial',
        'behavirla', 'behavirol', 'behvioral', 'behaviroal', 'behavorial',
        'behevioural', 'behevioral', 'behvioral', 'behviorla'
    ]
    return any(variant in text for variant in behavioral_variants)

def is_improvement_question(message):
    """Detect if the user is asking how to improve."""
    if not message:
        return False
    text = message.lower()
    improve_keywords = [
        'improve', 'better', 'behtar', 'behtari', 'kaise improve', 'kaise behtar',
        'tips', 'guidance', 'recommend', 'kese improve', 'kese behtar'
    ]
    return any(keyword in text for keyword in improve_keywords)

def normalize_text(text):
    """Normalize text for fuzzy matching."""
    if not text:
        return ''
    return re.sub(r'[^a-z0-9\s]+', ' ', text.lower()).strip()

def semantic_contains(text, keywords, threshold=0.87):
    """Fuzzy-match keywords in text to reduce strict exact matching."""
    if not text:
        return False
    normalized = normalize_text(text)
    if not normalized:
        return False
    # Direct substring match first (fast path)
    for kw in keywords:
        kw_norm = normalize_text(kw)
        if kw_norm and kw_norm in normalized:
            return True
    tokens = normalized.split()
    for kw in keywords:
        kw_norm = normalize_text(kw)
        if not kw_norm:
            continue
        if ' ' in kw_norm:
            # Multi-word keyword: match all parts fuzzily or overall similarity
            parts = kw_norm.split()
            if all(
                any(difflib.SequenceMatcher(None, part, tok).ratio() >= threshold for tok in tokens)
                for part in parts
            ):
                return True
            if difflib.SequenceMatcher(None, kw_norm, normalized).ratio() >= threshold:
                return True
        else:
            for tok in tokens:
                if difflib.SequenceMatcher(None, kw_norm, tok).ratio() >= threshold:
                    return True
    return False

def get_db_question_keywords():
    """Extract keywords from question tables in the database (cached)."""
    now = datetime.utcnow()
    cached = _DB_KEYWORDS_CACHE.get("keywords")
    updated_at = _DB_KEYWORDS_CACHE.get("updated_at")
    if cached and updated_at and (now - updated_at).total_seconds() < _DB_KEYWORDS_TTL_SECONDS:
        return cached

    keywords = set()
    try:
        conn = get_pg_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND LOWER(table_name) LIKE '%question%'
                """
            )
            tables = [row[0] for row in cursor.fetchall() if row and row[0]]

            for table_name in tables:
                cursor.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    """,
                    (table_name,)
                )
                columns = cursor.fetchall() or []
                text_columns = [
                    col for col, dtype in columns
                    if dtype in ('text', 'character varying', 'varchar')
                ]
                # Prefer common question column names
                preferred = None
                for cand in ('question', 'questions', 'question_text', 'questiontext'):
                    if cand in text_columns:
                        preferred = cand
                        break
                if not preferred:
                    continue

                cursor.execute(
                    sql.SQL("SELECT {col} FROM {table} LIMIT 100").format(
                        col=sql.Identifier(preferred),
                        table=sql.Identifier(table_name)
                    )
                )
                rows = cursor.fetchall() or []
                for (text,) in rows:
                    if not text:
                        continue
                    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-\+]{2,}", str(text).lower())
                    for token in tokens:
                        if token in _KEYWORD_STOPWORDS:
                            continue
                        keywords.add(token)
                        if len(keywords) >= 400:
                            break
                    if len(keywords) >= 400:
                        break
                if len(keywords) >= 400:
                    break
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to load question keywords from DB: {e}")

    keyword_list = sorted(keywords)
    _DB_KEYWORDS_CACHE["keywords"] = keyword_list
    _DB_KEYWORDS_CACHE["updated_at"] = now
    return keyword_list

def is_generic_definition_request(message):
    """Detect generic 'what is this/that' requests that need context."""
    if not message:
        return False
    text = message.lower().strip()
    patterns = [
        r'^(what is this|what is that|what is it)\??$',
        r'^(what\'?s this|what\'?s that|what\'?s it)\??$',
        r'^(define this|define that|define it)\??$',
        r'^(describe this|describe that|describe it)\??$',
        r'^(explain this|explain that|explain it)\??$',
        r'^(meaning of this|meaning of that|meaning of it)\??$',
        r'^(tell me about this|tell me about that|tell me about it)\??$',
        r'^(what is|what\'?s|define|describe|explain)\s+(this|that|it)\??$',
        r'^(what is|what\'?s|define|describe|explain)\s*$',
    ]
    return any(re.match(p, text) for p in patterns)

def build_generic_definition_context_message(context):
    """Build a concrete prompt from context for generic definition requests."""
    current_question = (context or {}).get('currentQuestion')
    skill = (context or {}).get('skill')
    role = (context or {}).get('role')
    if current_question:
        return f"Explain this interview question clearly: {current_question}"
    if skill:
        return f"Explain the concept: {skill}"
    if role:
        return f"Explain key concepts for the role: {role}"
    return ""

AI_SKILL_FALLBACKS = [
    {
        "keywords": ["machine learning", "ml", "machine-learning"],
        "response": (
            "Machine learning is a field where models learn patterns from data to make "
            "predictions or decisions without being explicitly programmed. In interviews, "
            "focus on data, features, training vs. inference, evaluation metrics, and "
            "bias/variance tradeoffs."
        ),
    },
    {
        "keywords": ["deep learning", "dl", "deep-learning"],
        "response": (
            "Deep learning is a subset of machine learning that uses multi-layer neural "
            "networks to learn representations from data. Be ready to explain architectures, "
            "backpropagation, overfitting/regularization, and compute requirements."
        ),
    },
    {
        "keywords": ["data science", "datascience", "data-science"],
        "response": (
            "Data science combines statistics, programming, and domain knowledge to extract "
            "insights from data. Interview focus: data cleaning, EDA, feature engineering, "
            "modeling, and communicating results."
        ),
    },
    {
        "keywords": ["python"],
        "response": (
            "Python is a core interview skill for scripting, data work, and ML. Expect "
            "questions on data structures, complexity, and libraries like pandas, numpy, "
            "and scikit-learn."
        ),
    },
    {
        "keywords": ["sql"],
        "response": (
            "SQL is used to query and transform data. Interview focus: joins, aggregations, "
            "window functions, indexing basics, and query optimization."
        ),
    },
    {
        "keywords": ["docker"],
        "response": (
            "Docker is a containerization tool for packaging apps with dependencies. "
            "Be ready to explain images vs. containers, Dockerfile basics, and use cases."
        ),
    },
    {
        "keywords": ["aws", "amazon web services"],
        "response": (
            "AWS is a cloud platform offering services like compute, storage, databases, and "
            "serverless. Interview focus: core services (EC2, S3, RDS, Lambda), security, "
            "scalability, and cost tradeoffs."
        ),
    },
    {
        "keywords": ["kubernetes", "k8s"],
        "response": (
            "Kubernetes orchestrates containers at scale. Key interview topics: pods, "
            "deployments, services, config/secrets, and scaling."
        ),
    },
    {
        "keywords": ["lambda", "aws lambda"],
        "response": (
            "AWS Lambda runs serverless functions on demand. Interview focus: event-driven "
            "triggers, cold starts, execution limits, and use cases."
        ),
    },
    {
        "keywords": ["tensorflow", "tensor flow"],
        "response": (
            "TensorFlow is a deep learning framework. Be ready to discuss computation graphs, "
            "model training loops, and deployment options."
        ),
    },
    {
        "keywords": ["pytorch", "torch"],
        "response": (
            "PyTorch is a deep learning framework known for dynamic graphs. Interview focus: "
            "tensors, autograd, model training, and debugging."
        ),
    },
    {
        "keywords": ["nlp", "natural language processing"],
        "response": (
            "NLP deals with text and language data. Interview topics: tokenization, embeddings, "
            "transformers, evaluation metrics, and common tasks like classification or QA."
        ),
    },
]

def build_ai_skill_fallback(user_message_lower):
    """Return a concise fallback answer for common AI/ML/data/infra skills."""
    for entry in AI_SKILL_FALLBACKS:
        if semantic_contains(user_message_lower, entry["keywords"], threshold=0.84):
            return entry["response"]
    return (
        "Here is a concise interview-prep overview of that AI/ML topic. If you want depth, "
        "tell me the specific subtopic you want to focus on."
    )

def build_rubric_response(interview_type, include_improvement=False, include_all=False):
    """Build a direct rubric-based response without LLM."""
    def render_one(rubric_type):
        normalized_type = rubric_type.lower() if rubric_type else 'default'
        config = get_interview_config(normalized_type)
        label_map = {
            'behavioral': 'Behavioral',
            'technical': 'Technical',
            'conceptual': 'Conceptual',
            'default': 'Technical/Other'
        }
        title = label_map.get(normalized_type, 'Interview')

        lines = [
            f"{title} questions are evaluated using these rubric criteria and weights:",
            ""
        ]
        for info in config['rubric_dimensions'].values():
            weight_pct = int(info['weight'] * 100)
            lines.append(f"- {info['label']} ({weight_pct}%)")

        # Provide full rubric details used by the system (load from docx)
        rubric_text, rubric_source = load_rubric_text(skill="", interview_type=normalized_type)
        if rubric_text:
            lines.extend([
                "",
                f"Detailed rubric used in the system (from {rubric_source}):",
                rubric_text.strip()
            ])

        if include_improvement:
            lines.extend([
                "",
                "How to improve based on this rubric:",
                "- Cover all parts thoroughly with structured answers.",
                "- Show accurate, role‑relevant knowledge and examples.",
                "- Communicate clearly and organize your points.",
            ])
            if normalized_type == 'behavioral':
                lines.append("- Follow STAR: Situation, Task, Action, Result.")

        return "\n".join(lines)

    if include_all:
        parts = [
            render_one('behavioral'),
            render_one('technical'),
            render_one('conceptual')
        ]
        return "\n\n---\n\n".join(parts)

    return render_one(interview_type)

def build_conversation_history(conversation_history):
    """Build conversation history messages from history array."""
    history_messages = []
    for msg in conversation_history[-10:]:
        if not (msg.get('role') and msg.get('content')):
            continue
        
        # Skip file previews in history to avoid large payloads
        if msg.get('file') and msg['file'].get('preview'):
            history_messages.append({
                "role": msg['role'],
                "content": msg.get('content', '[File attached]')
            })
        else:
            history_messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
    return history_messages

def count_history_roles(conversation_history):
    """Count user/assistant roles in conversation history."""
    counts = {"user": 0, "assistant": 0}
    for msg in conversation_history or []:
        role = msg.get('role')
        if role in counts:
            counts[role] += 1
    return counts

def get_recent_dialogue(conversation_history, max_messages=6):
    """Get the most recent user/assistant messages for follow-up context."""
    dialogue = []
    for msg in reversed(conversation_history or []):
        role = msg.get('role')
        content = msg.get('content')
        if role in ('user', 'assistant') and content:
            dialogue.append(f"{role}: {content}")
        if len(dialogue) >= max_messages:
            break
    return list(reversed(dialogue))

def get_last_assistant_message(conversation_history):
    """Fetch the latest assistant message from conversation history."""
    for msg in reversed(conversation_history or []):
        if msg.get('role') == 'assistant' and msg.get('content'):
            return msg['content']
    return ''

def is_feedback_question(message):
    """Detect if the user is asking about received feedback."""
    if not message:
        return False
    text = message.lower()
    feedback_keywords = [
        'feedback', 'review', 'evaluation', 'assessment', 'score',
        'remarks', 'comments', 'performance', 'improvement',
        'strength', 'weakness', 'areas for improvement',
        'behtari', 'kamzori', 'score', 'feedback ka', 'feedback me',
        'feedback mein', 'review ka', 'review me', 'evaluation ka'
    ]
    return any(keyword in text for keyword in feedback_keywords)

def extract_feedback_text(message):
    """Try to extract feedback text from the user's message."""
    if not message:
        return ''
    # Look for quoted feedback
    quoted = re.findall(r'["\']([^"\']{10,})["\']', message)
    if quoted:
        return quoted[0].strip()

    # Look for common feedback markers
    patterns = [
        r'feedback\s*[:\-]\s*(.+)$',
        r'feedback\s*(?:mila|tha|hai|me|mein)\s*[:\-]?\s*(.+)$',
        r'comments?\s*[:\-]\s*(.+)$',
        r'evaluation\s*[:\-]\s*(.+)$',
        r'assessment\s*[:\-]\s*(.+)$'
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return ''

def build_feedback_missing_response():
    """Response when feedback text is missing."""
    return (
        "I can explain your feedback, but I need the exact feedback text you received. "
        "Please paste the feedback (or the score/strengths/areas for improvement) so I can "
        "explain what it means for your performance."
    )

def build_feedback_fallback_response(feedback_text):
    """Fallback response when OpenAI is unavailable."""
    if not feedback_text:
        return build_feedback_missing_response()
    response_lines = [
        "Based on the feedback you shared:",
        f"- Feedback: {feedback_text}",
        "What it implies:",
        "- It highlights the specific areas mentioned above as the main gaps in your response.",
        "- Focus your next attempts on addressing those points directly, using clear structure and concrete examples."
    ]
    return "\n".join(response_lines)

def process_image_file(file_data, user_message):
    """Process image file and return user content array."""
    file_type = file_data.get('type', '')
    file_content = file_data.get('content', '')
    file_name = file_data.get('name', 'file')
    
    logger.info(f"Processing image: {file_name}, content length: {len(file_content) if file_content else 0}")
    
    # Prepare image URL
    image_url = file_content if file_content and file_content.startswith('data:') else None
    if not image_url and file_content:
        image_url = f"data:{file_type};base64,{file_content}"
    
    if not image_url:
        logger.error(f"Empty file content for image: {file_name}")
        return [{
            "type": "text",
            "text": f"I received an image file '{file_name}', but there was an error processing it. Please try uploading again."
        }]
    
    logger.info(f"Adding image to message, URL prefix: {image_url[:50]}...")
    
    # Build prompt text
    prompt_text = user_message if user_message else "Analyze this image in detail. Describe everything you see including any text, logos, diagrams, colors, layout, and other visual elements. Be thorough and specific."
    
    return [
        {"type": "text", "text": prompt_text},
        {"type": "image_url", "image_url": {"url": image_url}}
    ]

def process_text_file(file_data, user_message):
    """Process text file and return user content array."""
    file_type = file_data.get('type', '')
    file_content = file_data.get('content', '')
    file_name = file_data.get('name', 'file')
    
    text_extensions = ('.txt', '.md', '.py', '.js', '.java', '.cpp', '.c', '.html', '.css', '.json')
    is_text_file = file_type.startswith('text/') or file_name.endswith(text_extensions)
    
    if not is_text_file:
        return [{
            "type": "text",
            "text": f"I received a file '{file_name}' of type '{file_type}'. However, I can only analyze text files and images. Please describe what you need help with regarding this file."
        }]
    
    text_content = f"Here is the content of the file '{file_name}':\n\n{file_content}\n\n"
    if user_message:
        text_content += f"\n\n{user_message}"
    else:
        text_content += "Please analyze this file and help me understand it. Answer any questions I have about it."
    
    return [{"type": "text", "text": text_content}]

def build_user_content(file_data, user_message):
    """Build user content array from file data and user message."""
    if not file_data:
        return [{"type": "text", "text": user_message}] if user_message else []
    
    file_type = file_data.get('type', '')
    file_name = file_data.get('name', 'file')
    
    logger.info(f"Processing file: {file_name}, type: {file_type}")
    
    if file_type.startswith('image/'):
        return process_image_file(file_data, user_message)
    
    return process_text_file(file_data, user_message)

def select_model(file_data, default_model):
    """Select appropriate OpenAI model based on file type."""
    model = os.getenv("OPENAI_MODEL", default_model)
    
    has_image = file_data and file_data.get('type', '').startswith('image/')
    if not has_image:
        return model
    
    vision_models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-vision-preview', 'gpt-4-turbo']
    if model not in vision_models:
        model = "gpt-4o"
        logger.info(f"Switching to vision-capable model: {model} for image analysis")
    else:
        logger.info(f"Using vision-capable model: {model} for image analysis")
    
    return model

def add_user_message(messages, user_content):
    """Add user message to messages array."""
    if not user_content:
        logger.warning("Empty user_content, this should not happen")
        return False
    
    # Simple text message
    if len(user_content) == 1 and user_content[0].get('type') == 'text':
        messages.append({
            "role": "user",
            "content": user_content[0]['text']
        })
        logger.info(f"Added simple text message: {user_content[0]['text'][:100]}...")
        return True
    
    # Multi-modal message (text + image or multiple parts)
    messages.append({
        "role": "user",
        "content": user_content
    })
    logger.info(f"Added multi-modal message with {len(user_content)} parts")
    return True

@app.route('/api/chatbot', methods=['POST', 'OPTIONS'])
def chatbot():
    """Chatbot endpoint for interview preparation assistance.
    Handles technical, conceptual, and behavioral questions and tips.
    """
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return create_cors_options_response('POST, OPTIONS')
    
    try:
        data = request.json
        raw_user_message = data.get('message', '').strip()
        user_message = raw_user_message
        context = data.get('context', {})
        conversation_history = data.get('conversationHistory', [])

        # Log received data for debugging
        logger.info(f"Received chatbot request - message: {user_message[:50] if user_message else 'None'}")

        # Validate input
        if not raw_user_message:
            return jsonify({
                'success': False,
                'message': 'Message is required'
            }), 400

        last_assistant = get_last_assistant_message(conversation_history)
        role_counts = count_history_roles(conversation_history)
        has_prior_exchange = role_counts["assistant"] >= 1 and role_counts["user"] >= 1
        is_follow_up = bool(last_assistant and has_prior_exchange)

        # If this is a follow-up, enrich the prompt with last assistant reply
        if is_follow_up:
            recent_dialogue = "\n".join(get_recent_dialogue(conversation_history, max_messages=6))
            trimmed = last_assistant[:1200]
            user_message = (
                "Follow-up question based on the recent assistant response(s).\n"
                "Recent dialogue:\n"
                f"{recent_dialogue}\n\n"
                "Most recent assistant answer:\n"
                f"{trimmed}\n\n"
                f"User follow-up: {raw_user_message}"
            )

        # Pre-check for obvious off-topic questions
        user_message_lower = raw_user_message.lower()

        # Handle generic definition requests like "what is this"
        if is_generic_definition_request(raw_user_message):
            contextual_prompt = build_generic_definition_context_message(context)
            if contextual_prompt:
                raw_user_message = contextual_prompt
                user_message = contextual_prompt
                user_message_lower = raw_user_message.lower()
            else:
                return jsonify({
                    'success': True,
                    'response': "Please mention the exact topic you want defined (e.g., 'what is machine learning?')."
                })
        off_topic_keywords = [
            'movie', 'movies', 'film', 'cinema', 'actor', 'actress', 'celebrity',
            'cook', 'cooking', 'recipe', 'food', 'restaurant', 'dish',
            'travel', 'vacation', 'trip', 'tourist', 'destination', 'hotel',
            'weather', 'temperature', 'climate',
            'sport', 'football', 'cricket', 'basketball', 'game', 'gaming',
            'dating', 'relationship', 'love', 'marriage',
            'news', 'politics', 'election', 'government',
            'music', 'song', 'singer', 'album',
            'shopping', 'buy', 'purchase', 'price'
        ]
        
        # Check if message contains off-topic keywords and no interview-related keywords
        interview_keywords = [
            'interview', 'coding', 'algorithm', 'technical', 'behavioral',
            'star method', 'resume', 'cv', 'job', 'career', 'preparation',
            'programming', 'code', 'software', 'developer', 'engineer',
            'question', 'answer', 'practice', 'prep',
            'interview preparation question', 'help me understand', 'how to answer'
        ]

        # Always-allowed AI/ML/data/infra skills (common variants included)
        ai_skill_keywords = [
            'python', 'sql', 'docker', 'kubernetes', 'k8s', 'lambda', 'aws',
            'machine learning', 'ml', 'deep learning', 'dl',
            'data science', 'datascience', 'data-science',
            'tensorflow', 'tensor flow', 'pytorch', 'torch',
            'nlp', 'natural language processing',
            'ai', 'artificial intelligence',
            'mlops', 'model training', 'training data', 'neural network'
        ]

        # Broader technical/conceptual keywords that should always get a response
        technical_keywords = [
            'algorithm', 'data structure', 'complexity', 'big o', 'time complexity',
            'space complexity', 'hash', 'hashing', 'tree', 'graph', 'stack', 'queue',
            'array', 'linked list', 'binary search', 'sorting', 'dynamic programming',
            'recursion', 'oop', 'object oriented', 'design pattern', 'system design',
            'api', 'rest', 'graphql', 'database', 'sql', 'nosql', 'index',
            'network', 'tcp', 'udp', 'http', 'https', 'latency', 'throughput',
            'distributed system', 'microservices', 'cache', 'redis',
            'cloud', 'aws', 'gcp', 'azure', 'container', 'docker', 'kubernetes',
            'linux', 'git', 'ci/cd', 'pipeline', 'security', 'encryption',
            'machine learning', 'deep learning', 'neural network', 'model',
            'training', 'inference', 'overfitting', 'underfitting', 'bias', 'variance',
            'statistics', 'probability', 'linear algebra', 'calculus'
        ]
        # Add keywords dynamically from question tables (cached)
        technical_keywords.extend(get_db_question_keywords())

        # Include platform-specific roles/skills and interview types as valid context
        platform_keywords = []
        for role, skills in PLATFORM_SKILLS.items():
            platform_keywords.append(role.lower())
            platform_keywords.extend([skill.lower() for skill in skills])
        interview_type_keywords = [
            key.lower() for key in INTERVIEW_TYPE_CONFIG.keys() if key.lower() != 'default'
        ]
        
        # Check if this is an "Ask AI" question (from Ask AI button)
        is_ask_ai_question = 'interview preparation question' in user_message_lower or 'help me understand and answer this interview question' in user_message_lower
        
        has_off_topic = any(keyword in user_message_lower for keyword in off_topic_keywords)
        has_ai_skill_context = semantic_contains(raw_user_message, ai_skill_keywords)
        has_technical_context = semantic_contains(raw_user_message, technical_keywords)
        has_platform_skill_match = semantic_contains(raw_user_message, platform_keywords)
        has_db_keyword_match = semantic_contains(raw_user_message, get_db_question_keywords())

        # Allow response if any keyword matches platform skills or DB questions
        has_db_or_skill_match = has_platform_skill_match or has_db_keyword_match

        has_interview_context = (
            semantic_contains(raw_user_message, interview_keywords)
            or any(keyword in user_message_lower for keyword in interview_type_keywords)
            or is_ask_ai_question
            or has_ai_skill_context
            or has_technical_context
            or has_db_or_skill_match
            or is_follow_up
        )
        
        redirect_message = (
            "I'm specifically designed to help with interview preparation only. I can assist you with technical interview questions, "
            "behavioral interview tips, coding problems, interview strategies, and career preparation. How can I help you prepare for your interview?"
        )
        
        # If has off-topic keywords but no interview context, redirect immediately
        # BUT skip redirect if this is an "Ask AI" question
        if has_off_topic and not has_interview_context and not is_ask_ai_question:
            return jsonify({
                'success': True,
                'response': redirect_message
            })

        # Feedback-specific handling: require the actual feedback text
        if is_feedback_question(raw_user_message):
            feedback_text = extract_feedback_text(raw_user_message)
            if not feedback_text:
                return jsonify({
                    'success': True,
                    'response': build_feedback_missing_response()
                })

        # If user asks about rubric basis and mentions a specific interview type,
        # ensure the rubric context matches that type.
        if is_rubric_question(raw_user_message):
            explicit_type = None
            if is_behavioral_mention(user_message_lower):
                explicit_type = 'behavioral'
            elif 'technical' in user_message_lower:
                explicit_type = 'technical'
            elif 'conceptual' in user_message_lower:
                explicit_type = 'conceptual'

            if explicit_type:
                context = {**context, 'interviewType': explicit_type}
                rubric_reply = build_rubric_response(
                    context.get('interviewType'),
                include_improvement=is_improvement_question(raw_user_message)
                )
            else:
                rubric_reply = build_rubric_response(
                    None,
                    include_improvement=is_improvement_question(raw_user_message),
                    include_all=True
                )
            return jsonify({
                'success': True,
                'response': rubric_reply
            })

        # Build system prompt
        system_prompt = """You are an Interview Preparation Assistant EXCLUSIVELY designed for interview preparation. You MUST NOT answer any questions outside interview preparation.

STRICT RULES (FOLLOW EXACTLY):
1. ALWAYS ANSWER questions about:
   - Technical interview prep (coding, algorithms, data structures, system design)
   - Behavioral interview prep (STAR method, common questions, examples)
   - Interview strategy, tips, and career prep related to interviews
   - Coding problems and solutions for interview practice
   - Interview feedback and rubric-based evaluation
   - Core AI/ML and data/infra topics commonly asked in interviews
   - Platform interview types, roles, and skills listed in "Platform Skills"

2. ALWAYS ANSWER questions about these skills (even if "interview" is NOT mentioned):
   Python, SQL, Docker, Kubernetes, AWS/Lambda, Machine Learning, Deep Learning,
   Data Science, TensorFlow, PyTorch, NLP

3. NEVER ANSWER questions about (redirect immediately):
   - Movies, entertainment, TV shows, celebrities
   - Cooking, recipes, food
   - Travel, vacation, hotels
   - Sports, games, hobbies
   - Dating, relationships, personal advice
   - Politics, news, current events
   - General knowledge not tied to interview prep

4. Off-topic redirect response (use EXACTLY):
   "I'm specifically designed to help with interview preparation only. I can assist you with technical interview questions, behavioral interview tips, coding problems, interview strategies, and career preparation. How can I help you prepare for your interview?"

5. Follow-up questions:
   - If the user asks a follow-up about your previous response, answer directly and stay on-topic.
   - If the follow-up is ambiguous, ask a short clarification only for that part.
   - If multiple questions are asked, answer each in order.

6. Feedback & Rubrics:
   - If user asks about feedback, base the response ONLY on feedback text in history.
   - If user asks how evaluation works, use "Rubric Basis" from context and tie improvements to it.

CRITICAL: Never answer off-topic questions. Always redirect immediately with the standard message above."""

        # Build messages
        context_info = build_context_info(context)
        messages = [{"role": "system", "content": system_prompt + context_info}]
        messages.extend(build_conversation_history(conversation_history))

        # Add user message
        messages.append({
            "role": "user",
            "content": user_message
            })

        # Get OpenAI client and generate response
        try:
            client = get_openai_client()
            model = "gpt-4o-mini"
            
            logger.info(f"Calling OpenAI API with model: {model}, message count: {len(messages)}")
            
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            logger.info(f"OpenAI API response received successfully")
            assistant_response = completion.choices[0].message.content
            logger.info(
                "Chatbot flags - off_topic=%s, interview_context=%s, ai_skill=%s, technical=%s, follow_up=%s",
                has_off_topic, has_interview_context, has_ai_skill_context, has_technical_context, is_follow_up
            )
            logger.info(
                "Chatbot response preview: %s",
                (assistant_response or '')[:200].replace('\n', ' ')
            )
            if not assistant_response or not assistant_response.strip():
                if has_ai_skill_context or has_technical_context:
                    assistant_response = build_ai_skill_fallback(user_message_lower)
            elif (has_ai_skill_context or has_technical_context) and assistant_response.strip() == redirect_message:
                assistant_response = build_ai_skill_fallback(user_message_lower)

            return jsonify({
                'success': True,
                'response': assistant_response
            })
        except Exception as openai_error:
            logger.error(f"OpenAI API error: {str(openai_error)}")
            # Check if it's an API key issue
            if "api key" in str(openai_error).lower() or "authentication" in str(openai_error).lower():
                if is_feedback_question(user_message):
                    fallback_text = extract_feedback_text(user_message)
                    return jsonify({
                        'success': True,
                        'response': build_feedback_fallback_response(fallback_text)
                    })
                return jsonify({
                    'success': False,
                    'message': 'OpenAI API key not configured. Please set OPENAI_API_KEY in your .env file.'
                }), 500
            else:
                if is_feedback_question(user_message):
                    fallback_text = extract_feedback_text(user_message)
                    return jsonify({
                        'success': True,
                        'response': build_feedback_fallback_response(fallback_text)
                    })
                return jsonify({
                    'success': False,
                    'message': f'Error calling OpenAI API: {str(openai_error)}'
                }), 500

    except Exception as e:
        logger.error(f"Chatbot error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing chatbot request: {str(e)}'
        }), 500

@app.route('/api/next-question', methods=['POST'])
def generate_next_question():
    """Generate a follow-up question based on user's last answer and current context.
    Body: { last_question: str, last_answer: str, role?: str, interview_type?: str, conversation?: [ {role, content} ] }
    Returns: { success, question, intent }
    """
    try:
        data = request.get_json(force=True)
        last_question = (data or {}).get('last_question', '')
        last_answer = (data or {}).get('last_answer', '')
        role = (data or {}).get('role', 'AI Interviewer')
        interview_type = (data or {}).get('interview_type', 'conceptual')
        conversation = (data or {}).get('conversation') or []

        # Simple intent heuristics
        text_low = (last_answer or '').lower().strip()
        # Check if answer is empty or too short to be meaningful
        if not text_low or len(text_low) < 3:
            return jsonify({ 'success': False, 'intent': 'silence', 'message': 'Answer too short or empty' })
        # Check for common filler/noise patterns
        if re.match(r'^(uh+|um+|er+|ah+|hmm+|\.{3,}|\s+)$', text_low):
            return jsonify({ 'success': False, 'intent': 'noise', 'message': 'Answer contains only filler words' })
        if any(p in text_low for p in ['give me a moment', 'one minute', 'wait a second', 'need time']):
            return jsonify({ 'success': True, 'intent': 'ask_time', 'question': 'Sure, I will give you a moment. Ready when you are.' })

        # Use LLM to craft a targeted follow-up grounded in the user answer
        try:
            from openai import OpenAI
            client = OpenAI()
            system_msg = (
                "You are an HR-friendly interviewer. Based on the candidate's answer, "
                "generate ONE concise, relevant follow-up question that probes depth, examples, or trade-offs. "
                "Keep it under 20 words. Do not add commentary."
            )
            messages = [{ 'role': 'system', 'content': system_msg }]
            for m in conversation[-6:]:
                if isinstance(m, dict) and m.get('role') and m.get('content'):
                    messages.append({ 'role': m['role'], 'content': m['content'] })
            user_prompt = (
                f"Interview type: {interview_type}\n"
                f"Previous question: {last_question}\n"
                f"Candidate answer: {last_answer}\n\n"
                "Now produce only the follow-up question:"
            )
            messages.append({ 'role': 'user', 'content': user_prompt })
            comp = client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                temperature=0.7,
                messages=messages
            )
            q = comp.choices[0].message.content.strip()
            return jsonify({ 'success': True, 'intent': 'follow_up', 'question': q })
        except Exception as e:
            # Fallback: generic probing question
            fallback = 'Could you share a concrete example or metrics to support that?'
            return jsonify({ 'success': True, 'intent': 'follow_up', 'question': fallback, 'message': str(e) })
    except Exception as e:
        return jsonify({ 'success': False, 'message': f'Error generating next question: {e}' }), 500


@app.route('/api/evaluate', methods=['POST'])
def evaluate_answer():
    """Evaluate a text answer against rubric using LLM.
    Expected JSON: { question, answer, job_title?, skills?, interview_type? }
    """
    try:
        data = request.get_json(force=True, silent=False)
        question = data.get('question')
        answer = data.get('answer')
        job_title = data.get('job_title', 'Software Engineer')
        skills = data.get('skills', '')
        interview_type = data.get('interview_type', '')  # Get interview type

        if not question or not answer:
            return jsonify({
                'success': False,
                'message': 'Both question and answer are required.'
            }), 400

        result = process_text_response(answer, question, job_title=job_title, skills=skills, interview_type=interview_type)
        
        # Log which model was used for evaluation
        if result.get('success') and result.get('model_used'):
            logger.info(f"Evaluation completed using model: {result.get('model_used')}")
            print(f"[API /api/evaluate] Model used for evaluation: {result.get('model_used')}")
        
        return jsonify(result), (200 if result.get('success') else 500)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error during evaluation: {str(e)}'
        }), 500


@app.route('/api/evaluation-model', methods=['GET'])
def get_evaluation_model():
    """Get the current model configuration for Skill Prep evaluation."""
    try:
        skill_prep_model = os.getenv("SKILL_PREP_MODEL", "gpt-5.2-thinking")
        default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        return jsonify({
            'success': True,
            'skill_prep_model': skill_prep_model,
            'default_model': default_model,
            'message': f'Skill Prep evaluation uses: {skill_prep_model} (falls back to {default_model} if unavailable)'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting model configuration: {str(e)}'
        }), 500


if __name__ == '__main__':
    load_dotenv()
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
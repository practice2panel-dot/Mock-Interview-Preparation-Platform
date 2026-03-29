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
import logging
import traceback
from voice_processor import process_text_response, get_openai_client
from rubric_loader import load_rubric_text
from random import shuffle
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


def resolve_mock_interview_skills(job_role, client_skills=None):
    """
    Skills used to resolve DB tables like {interview_type}_python.

    If job_role is in PLATFORM_SKILLS, the server list is authoritative (same as Skill Prep
    when that role exists on the server).

    If the role is missing on the server (stale deploy) but the frontend sends `skills`,
    use that list so question loading matches /api/questions/<type>/<skill> behavior.
    """
    if job_role in PLATFORM_SKILLS:
        return list(PLATFORM_SKILLS[job_role])
    if isinstance(client_skills, list) and client_skills:
        cleaned = [str(s).strip() for s in client_skills if str(s).strip()]
        return cleaned if cleaned else None
    return None


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
from cors_config import get_allowed_origins

allowed_origins = get_allowed_origins()

# Apply CORS globally to all routes (more reliable than resource-specific)
CORS(app, 
     supports_credentials=True, 
     origins=allowed_origins,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Accept", "Origin"],
     expose_headers=["Set-Cookie"])

# Helper function for CORS OPTIONS responses
def create_cors_options_response(methods="GET, POST, PUT, DELETE, OPTIONS"):
    """Create a standardized CORS OPTIONS response."""
    origin = request.headers.get('Origin', 'http://localhost:3000')
    # Validate origin
    if origin.rstrip('/') not in allowed_origins:
        origin = 'http://localhost:3000'
    response = jsonify({'success': True})
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Origin'
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
        origin = request.headers.get('Origin', 'http://localhost:3000')
        if origin.rstrip('/') in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Origin'
    
    return response

# Register auth blueprint
app.register_blueprint(auth_bp)

# Error handler to ensure CORS headers on all errors
@app.errorhandler(500)
def handle_500_error(e):
    """Handle 500 errors with CORS headers"""
    origin = request.headers.get('Origin', 'http://localhost:3000')
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
    
    if origin.rstrip('/') in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Origin'
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
                    SELECT role, interview_type, duration_seconds, created_at
                    FROM mock_interview_sessions
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 10
                    """,
                    (session.get('user_id'),)
                )
                mock_history = [
                    {
                        'role': row[0],
                        'interview_type': row[1],
                        'duration_seconds': int(row[2] or 0),
                        'created_at': row[3].isoformat()
                    }
                    for row in cursor.fetchall()
                ]

                cursor.execute(
                    """
                    SELECT COUNT(*) FROM mock_interview_sessions
                    WHERE user_id = %s
                    """,
                    (session.get('user_id'),)
                )
                mock_count = cursor.fetchone()[0]

                cursor.execute(
                    """
                    SELECT interview_type, COUNT(*)
                    FROM mock_interview_sessions
                    WHERE user_id = %s AND interview_type IS NOT NULL
                    GROUP BY interview_type
                    ORDER BY interview_type
                    """,
                    (session.get('user_id'),)
                )
                mock_breakdown = [{'interview_type': row[0], 'count': int(row[1])} for row in cursor.fetchall()]

                cursor.execute(
                    """
                    SELECT COALESCE(SUM(duration_seconds), 0)
                    FROM mock_interview_sessions
                    WHERE user_id = %s
                    """,
                    (session.get('user_id'),)
                )
                mock_time_seconds = cursor.fetchone()[0] or 0

                cursor.execute(
                    """
                    SELECT DISTINCT DATE(created_at) AS activity_date
                    FROM mock_interview_sessions
                    WHERE user_id = %s
                    ORDER BY activity_date DESC
                    """,
                    (session.get('user_id'),)
                )
                mock_activity_dates = [row[0].isoformat() for row in cursor.fetchall()]

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
                'mock_interview_history': list(reversed(mock_history)),
                'mock_interview_count': int(mock_count or 0),
                'mock_interview_breakdown': mock_breakdown,
                'mock_interview_time_seconds': int(mock_time_seconds or 0),
                'questions_total': int(questions_total or 0),
                'questions_time_seconds': int(questions_time_seconds or 0),
                'questions_breakdown': questions_breakdown,
                'skill_progress': skill_progress,
                'recent_questions': list(reversed(recent_questions)),
                'mock_activity_dates': mock_activity_dates
            }

            return jsonify({'success': True, 'summary': summary}), 200
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error loading dashboard summary: {str(e)}'}), 500

@app.route('/api/mock-interview/questions', methods=['POST'])
def get_mock_interview_questions():
    """Get questions for all skills of a job role for mock interview"""
    try:
        data = request.get_json()
        job_role = data.get('job_role', '')
        interview_type = data.get('interview_type', 'technical')
        
        if not job_role:
            return jsonify({
                'success': False,
                'message': 'Job role is required'
            }), 400
        
        client_skills = data.get('skills')
        skills = resolve_mock_interview_skills(job_role, client_skills)
        if not skills:
            return jsonify({
                'success': False,
                'message': (
                    f'Job role "{job_role}" is not recognized on the server and no valid skills '
                    f'list was sent. Update the backend or ensure the client sends a skills array.'
                )
            }), 400
        
        all_questions = []
        questions_per_skill = 3
        min_questions = 15  # Target 15 questions total
        
        # Check if behavioral interview (dictionary-based check)
        normalized_type = interview_type.lower() if interview_type else 'default'
        is_behavioral = normalized_type == 'behavioral'
        
        # For behavioral interviews: fetch from single table
        # For other interviews: fetch from skill-specific tables
        table_name = get_question_table_name(interview_type)
        logger.info(f"Fetching questions from table: {table_name}")
        questions, error = get_questions_from_table(table_name)
        
        # Handle behavioral interviews (single table)
        behavioral_questions_processed = False
        if not error and questions and is_behavioral:
            logger.info(f"Found {len(questions)} behavioral questions in database")
            shuffle(questions)
            selected_questions = questions[:min(min_questions, len(questions))]
            logger.info(f"Selected {len(selected_questions)} behavioral questions for interview")
            for q in selected_questions:
                all_questions.append({
                    'question': q,
                    'skill': 'Behavioral',
                    'interview_type': interview_type
                })
            behavioral_questions_processed = True
        
        # Handle other interview types (skill-specific tables)
        if not behavioral_questions_processed:
            for skill in skills:
                table_name = get_question_table_name(interview_type, skill)
                questions, error = get_questions_from_table(table_name)
                
                if not error and questions:
                    shuffle(questions)
                    questions_to_take = min(questions_per_skill, len(questions))
                    selected_questions = questions[:questions_to_take]
                    for q in selected_questions:
                        all_questions.append({
                            'question': q,
                            'skill': skill,
                            'interview_type': interview_type
                        })
            
            # If we still don't have enough questions, try to get more from skills that have available questions
            # But limit to 15 questions total for interview
            max_questions = len(skills) * questions_per_skill
            if len(all_questions) < min_questions:
                for skill in skills:
                    if len(all_questions) >= max_questions:
                        break
                        
                    skill_lower = skill.lower().replace(' ', '')
                    table_name = f"{interview_type}_{skill_lower}"
                    
                    questions, error = get_questions_from_table(table_name)
                    if not error and questions:
                        shuffle(questions)
                        # Get questions we haven't already selected
                        existing_questions = [q['question'] for q in all_questions if q['skill'] == skill]
                        new_questions = [q for q in questions if q not in existing_questions]
                        
                        # Add more questions until we reach max_questions
                        needed = min(max_questions - len(all_questions), len(new_questions))
                        for q in new_questions[:needed]:
                            all_questions.append({
                                'question': q,
                                'skill': skill,
                                'interview_type': interview_type
                            })
            
            # Limit total questions to 12 maximum
            if len(all_questions) > max_questions:
                shuffle(all_questions)
                all_questions = all_questions[:max_questions]
        
        # Final shuffle to randomize the order
        shuffle(all_questions)
        
        if not all_questions:
            table_name = get_question_table_name(interview_type)
            normalized_type = interview_type.lower() if interview_type else 'default'
            is_behavioral = normalized_type == 'behavioral'
            error_msg = f'No questions found for {interview_type} interview type. Please check if the "{table_name}" table exists in the database and has questions.'
            if not is_behavioral:
                error_msg += f' Please check if tables like "{interview_type}_<skill>" exist in the database.'
            logger.error(error_msg)
            return jsonify({
                'success': False,
                'message': error_msg
            }), 404
        
        logger.info(f"Successfully fetched {len(all_questions)} {interview_type} questions for {job_role}")
        return jsonify({
            'success': True,
            'questions': all_questions,
            'total_questions': len(all_questions)
        })
        
    except Exception as e:
        logger.error(f"Error fetching mock interview questions: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

def format_rubric_feedback(feedback_data, candidate_name, job_role, interview_type):
    """Format structured rubric feedback into a readable text format"""
    try:
        from datetime import datetime
        
        lines = []
        # Header
        lines.append(f"INTERVIEW FEEDBACK REPORT")
        lines.append(f"{'='*60}")
        lines.append(f"Candidate: {candidate_name}")
        lines.append(f"Position: {job_role}")
        lines.append(f"Interview Type: {interview_type.title()}")
        lines.append(f"Interview Details: {datetime.now().strftime('%B %d, %Y')} at {datetime.now().strftime('%I:%M %p')} | Interviewer: AI Interviewer")
        lines.append(f"{'='*60}\n")
        
        # Overall Score
        overall_score = feedback_data.get('overall_score', 0)
        lines.append(f"OVERALL PERFORMANCE SCORE: {overall_score:.2f}/10\n")
        
        # Overall Feedback (use summary as overall feedback)
        overall_feedback = feedback_data.get('summary', '')
        if overall_feedback:
            lines.append("OVERALL FEEDBACK")
            lines.append("-" * 60)
            lines.append(overall_feedback)
            lines.append("")
        
        # Key Strengths
        if feedback_data.get('key_strengths'):
            lines.append("KEY STRENGTHS")
            lines.append("-" * 60)
            for i, strength in enumerate(feedback_data['key_strengths'], 1):
                lines.append(f"{i}. {strength}")
            lines.append("")
        
        # Areas for Improvement
        if feedback_data.get('areas_for_improvement'):
            lines.append("AREAS FOR IMPROVEMENT")
            lines.append("-" * 60)
            for i, area in enumerate(feedback_data['areas_for_improvement'], 1):
                lines.append(f"{i}. {area}")
            lines.append("")
        
        # Recommendations
        if feedback_data.get('recommendations'):
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 60)
            for i, rec in enumerate(feedback_data['recommendations'], 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        # Performance Summary (at the end, only if different from overall feedback)
        summary = feedback_data.get('summary', '')
        if summary and summary != overall_feedback:
            lines.append("PERFORMANCE SUMMARY")
            lines.append("-" * 60)
            lines.append(summary)
            lines.append("")
        
        lines.append(f"{'='*60}")
        lines.append("This evaluation was conducted using standardized rubrics to ensure fair and objective assessment.")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error formatting feedback: {str(e)}")
        # Fallback to simple format
        score = feedback_data.get('overall_score', 0)
        if score <= 10:
            score = score * 10
        strengths = ', '.join(feedback_data.get('key_strengths', [])) or 'None listed'
        weaknesses = ', '.join(feedback_data.get('weaknesses', feedback_data.get('areas_for_improvement', []))) or 'None listed'
        return f"INTERVIEW FEEDBACK REPORT\n{'='*60}\nCandidate: {candidate_name}\nPosition: {job_role}\nInterview Type: {interview_type.title()}\n{'='*60}\n\nOverall Score: {score:.0f}/100\n\nStrengths: {strengths}\nWeaknesses: {weaknesses}\n"

def format_simple_feedback(feedback_data, candidate_name, job_role, interview_type):
    """Format simple LLM feedback (no rubrics) into a readable text format"""
    try:
        from datetime import datetime
        
        lines = []
        # Header
        lines.append(f"INTERVIEW FEEDBACK REPORT")
        lines.append(f"{'='*60}")
        lines.append(f"Candidate: {candidate_name}")
        lines.append(f"Position: {job_role}")
        lines.append(f"Interview Type: {interview_type.title()}")
        lines.append(f"Interview Details: {datetime.now().strftime('%B %d, %Y')} at {datetime.now().strftime('%I:%M %p')} | Interviewer: AI Interviewer")
        lines.append(f"{'='*60}\n")
        
        # Overall Score (0-100 scale)
        overall_score = feedback_data.get('overall_score', 0)
        # Convert to 0-100 if it's in 0-10 scale
        if overall_score <= 10:
            overall_score = overall_score * 10
        lines.append(f"OVERALL PERFORMANCE SCORE: {overall_score:.0f}/100\n")
        
        # Key Strengths
        if feedback_data.get('key_strengths'):
            lines.append("STRENGTHS")
            lines.append("-" * 60)
            for i, strength in enumerate(feedback_data['key_strengths'], 1):
                lines.append(f"• {strength}")
            lines.append("")
        
        # Weaknesses (prefer weaknesses, fallback to areas_for_improvement)
        weaknesses = feedback_data.get('weaknesses') or feedback_data.get('areas_for_improvement', [])
        if weaknesses:
            lines.append("WEAKNESSES")
            lines.append("-" * 60)
            for i, weakness in enumerate(weaknesses, 1):
                lines.append(f"• {weakness}")
            lines.append("")
        
        # How to Improve (Actionable Suggestions)
        how_to_improve = feedback_data.get('how_to_improve') or feedback_data.get('recommendations', [])
        if how_to_improve:
            lines.append("HOW TO IMPROVE (ACTIONABLE SUGGESTIONS)")
            lines.append("-" * 60)
            for i, suggestion in enumerate(how_to_improve, 1):
                lines.append(f"• {suggestion}")
            lines.append("")
        
        # Recommended Topics
        if feedback_data.get('recommended_topics'):
            lines.append("RECOMMENDED NEXT TOPICS TO PREPARE")
            lines.append("-" * 60)
            for i, topic in enumerate(feedback_data['recommended_topics'], 1):
                lines.append(f"• {topic}")
            lines.append("")
        
        lines.append(f"{'='*60}")
        lines.append("This evaluation was conducted using AI-based natural language analysis.")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error formatting feedback: {str(e)}")
        # Fallback to simple format
        score = feedback_data.get('overall_score', 0)
        if score <= 10:
            score = score * 10
        strengths = ', '.join(feedback_data.get('key_strengths', [])) or 'None listed'
        weaknesses = ', '.join(feedback_data.get('weaknesses', feedback_data.get('areas_for_improvement', []))) or 'None listed'
        return f"INTERVIEW FEEDBACK REPORT\n{'='*60}\nCandidate: {candidate_name}\nPosition: {job_role}\nInterview Type: {interview_type.title()}\n{'='*60}\n\nOverall Score: {score:.0f}/100\n\nStrengths: {strengths}\nWeaknesses: {weaknesses}\n"


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


@app.route('/api/mock-interview/feedback', methods=['POST'])
def generate_interview_feedback():
    """Generate interview feedback using LLM (without rubrics - natural evaluation)"""
    try:
        data = request.get_json()
        conversation_history = data.get('conversation_history', [])
        job_role = data.get('job_role', '')
        interview_type = data.get('interview_type', 'technical')
        candidate_name = data.get('candidate_name', 'Candidate')
        
        # Validate conversation history
        if not conversation_history:
            return jsonify({
                'success': False,
                'message': 'Conversation history is required. No interview conversation found.'
            }), 400
        
        # Check if conversation history has meaningful content
        # Filter out empty or very short messages
        meaningful_messages = [
            msg for msg in conversation_history 
            if isinstance(msg, dict) and 
            msg.get('content') and 
            len(str(msg.get('content', '')).strip()) > 5
        ]
        
        if len(meaningful_messages) < 2:
            return jsonify({
                'success': False,
                'message': 'Insufficient conversation data. Please complete the interview before generating feedback.'
            }), 400
        
        # Check if there are user responses (candidate answers)
        user_messages = [
            msg for msg in meaningful_messages 
            if msg.get('role') == 'user' and len(str(msg.get('content', '')).strip()) > 10
        ]
        
        if len(user_messages) == 0:
            return jsonify({
                'success': False,
                'message': 'No candidate responses found in the conversation. Please participate in the interview before generating feedback.'
            }), 400
        
        # Log conversation stats
        logger.info(f"Generating LLM feedback (rubric-based) - {len(conversation_history)} total messages, {len(user_messages)} candidate responses")
        
        # Rubric-based evaluation for Mock Interview
        # Build conversation summary
        MAX_CONVERSATION_LENGTH = 8000  # Increased for better context
        conversation_summary = "\n\n--- INTERVIEW CONVERSATION HISTORY ---\n\n"
        conversation_count = {'assistant': 0, 'user': 0}
        total_length = 0
        
        # Process messages and limit total length to speed up LLM processing
        for idx, msg in enumerate(conversation_history):
            if isinstance(msg, dict) and msg.get('role') and msg.get('content'):
                role_label = "Interviewer" if msg['role'] == 'assistant' else "Candidate"
                content = str(msg.get('content', '')).strip()
                if content:
                    # Truncate very long messages to keep within limits
                    if len(content) > 400:
                        content = content[:400] + "... [truncated]"
                    
                    if len(content) > 500:
                        content = content[:500] + "... [truncated]"
                    
                    message_text = f"[{idx + 1}] {role_label}: {content}\n\n"
                    
                    if total_length + len(message_text) > MAX_CONVERSATION_LENGTH:
                        remaining = len(conversation_history) - idx
                        conversation_summary += f"\n[... {remaining} more messages truncated ...]\n\n"
                        break
                    
                    conversation_summary += message_text
                    total_length += len(message_text)
                    conversation_count[msg['role']] = conversation_count.get(msg['role'], 0) + 1
        
        conversation_summary += f"\n--- END OF CONVERSATION ---\n"
        conversation_summary += f"Total Messages: {len(conversation_history)} | Interviewer Questions: {conversation_count.get('assistant', 0)} | Candidate Responses: {conversation_count.get('user', 0)}\n"
        
        # Build system prompt with rubric-based evaluation
        system_prompt = f"""You are an expert interview evaluator providing comprehensive feedback for a {interview_type} interview for the position of {job_role}.

You are evaluating {candidate_name}'s interview performance. Analyze the conversation naturally and provide honest, constructive feedback.

EVALUATION GUIDELINES:
1. Evaluate ONLY based on the actual conversation history provided below
2. Be fair, objective, and evidence-based
3. If the candidate gave minimal responses or the interview was incomplete, reflect this honestly
4. Use the rubric below to score the interview; base scores on evidence from the conversation
5. Focus on what actually happened in the conversation

{conversation_summary}

RUBRIC (0-10 each):
- Relevance (40%): How well answers match the questions asked.
- Completeness (25%): Coverage of key points; depth of response.
- Clarity (20%): Communication structure, clarity, and confidence.
- Accuracy (15%): Correctness of information and reasoning.

Based on this conversation, provide comprehensive feedback in the following JSON format:
{{
  "overall_score": <0-100, overall performance score out of 100>,
  "rubric_scores": {{
    "relevance": {{ "score": <0-10>, "evidence": "specific examples from conversation" }},
    "completeness": {{ "score": <0-10>, "evidence": "specific examples from conversation" }},
    "clarity": {{ "score": <0-10>, "evidence": "specific examples from conversation" }},
    "accuracy": {{ "score": <0-10>, "evidence": "specific examples from conversation" }}
  }},
  "key_strengths": ["strength 1", "strength 2", "strength 3", "strength 4", "strength 5"],
  "weaknesses": ["weakness 1", "weakness 2", "weakness 3", "weakness 4"],
  "how_to_improve": ["actionable suggestion 1", "actionable suggestion 2", "actionable suggestion 3", "actionable suggestion 4"],
  "recommended_topics": ["topic 1", "topic 2", "topic 3", "topic 4", "topic 5"]
}}

IMPORTANT GUIDELINES:
- overall_score: Provide a score from 0-100 (not 0-10). This represents overall interview performance.
- rubric_scores: Provide 0-10 scores with evidence. Use these weights to compute overall_score:
  overall_score = (relevance×0.40 + completeness×0.25 + clarity×0.20 + accuracy×0.15) × 10
- key_strengths: List 3-5 clear strengths observed during the interview. Be specific and evidence-based.
- weaknesses: List 2-4 clear weaknesses or areas that need improvement. Use constructive, non-judgmental language.
- how_to_improve: Provide practical and specific steps the candidate can take to improve (e.g., topics to study, practice methods, skills to develop). Make these actionable.
- recommended_topics: Suggest 3-5 relevant topics based on the candidate's weak areas and the job role.

TONE REQUIREMENTS:
- Use bullet points format (already in arrays)
- Keep the tone motivating and professional
- DO NOT use harsh or judgmental language
- Focus on helping the candidate understand their mistakes and improve confidently
- Be encouraging but honest
- Base everything on actual evidence from the conversation"""
        
        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history to messages for context
        for msg in conversation_history:
            if isinstance(msg, dict) and msg.get('role') and msg.get('content'):
                content = str(msg.get('content', '')).strip()
                if content:
                    messages.append({
                        'role': msg['role'],
                        'content': content
                    })
        
        # Add final prompt
        messages.append({
            'role': 'user',
            'content': f'Please provide comprehensive feedback for {candidate_name}\'s {interview_type} interview performance based on the conversation above. Be natural, honest, and constructive.'
        })
        
        # Get OpenAI client and generate feedback
        try:
            client = get_openai_client()
            model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
            
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,  # Higher temperature for more natural feedback
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            
            feedback_json_str = completion.choices[0].message.content
            
            # Parse the JSON feedback
            try:
                feedback_data = json.loads(feedback_json_str)
                
                # Ensure overall_score is present and valid (0-100 scale)
                if 'overall_score' not in feedback_data:
                    feedback_data['overall_score'] = 50.0  # Default if not provided
                else:
                    score = float(feedback_data['overall_score'])
                    # If score is 0-10, convert to 0-100 scale
                    if score <= 10:
                        score = score * 10
                    feedback_data['overall_score'] = max(0, min(100, score))

                # Recalculate overall score from rubric_scores if present
                rubric_scores = feedback_data.get('rubric_scores', {})
                if isinstance(rubric_scores, dict) and rubric_scores:
                    weights = {
                        'relevance': 0.40,
                        'completeness': 0.25,
                        'clarity': 0.20,
                        'accuracy': 0.15
                    }
                    weighted_total = 0.0
                    for key, weight in weights.items():
                        raw_score = rubric_scores.get(key, {}).get('score', 0)
                        try:
                            score_value = float(raw_score)
                        except (TypeError, ValueError):
                            score_value = 0.0
                        score_value = max(0.0, min(10.0, score_value))
                        weighted_total += score_value * weight
                    feedback_data['overall_score'] = max(0.0, min(100.0, weighted_total * 10))

                # Note: guardrails removed; scoring now relies on rubric evaluation only
                
                # Ensure all required fields exist with defaults
                if 'key_strengths' not in feedback_data:
                    feedback_data['key_strengths'] = []
                if 'weaknesses' not in feedback_data:
                    # Fallback: use areas_for_improvement if weaknesses not present
                    feedback_data['weaknesses'] = feedback_data.get('areas_for_improvement', [])
                if 'how_to_improve' not in feedback_data:
                    # Fallback: use recommendations if how_to_improve not present
                    feedback_data['how_to_improve'] = feedback_data.get('recommendations', [])
                if 'recommended_topics' not in feedback_data:
                    feedback_data['recommended_topics'] = []
                
                # Format feedback for display (simple format, no rubrics)
                formatted_feedback = format_simple_feedback(feedback_data, candidate_name, job_role, interview_type)

                return jsonify({
                    'success': True,
                    'feedback': formatted_feedback,
                    'feedback_data': feedback_data,
                    'candidate_name': candidate_name,
                    'job_role': job_role,
                    'interview_type': interview_type
                })
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON feedback: {str(e)}")
                # Fallback to raw text
                return jsonify({
                    'success': True,
                    'feedback': feedback_json_str,
                    'candidate_name': candidate_name,
                    'job_role': job_role,
                    'interview_type': interview_type
                })
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error generating feedback: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error generating interview feedback: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500


@app.route('/api/mock-interview/get-assistant-config', methods=['POST'])
def get_assistant_config():
    """Get assistant configuration for VAPI Web SDK (no phone number required)
    
    For Web SDK, we can either:
    1. Return the assistant config directly (for inline assistant)
    2. Create an assistant via API and return assistantId (recommended)
    """
    try:
        import requests
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided in request'
            }), 400
            
        candidate_name = data.get('candidate_name', '')
        job_role = data.get('job_role', '')
        interview_type = data.get('interview_type', 'technical')
        questions = data.get('questions', [])
        system_message = data.get('system_message', '')
        assistant_message = data.get('assistant_message', '')
        
        logger.info(f"Getting assistant config for candidate: {candidate_name}, role: {job_role}, type: {interview_type}")
        
        # Get VAPI API key from environment
        vapi_api_key = os.getenv('VAPI_PRIVATE_KEY', '')
        if not vapi_api_key:
            return jsonify({
                'success': False,
                'message': 'VAPI API key not configured'
            }), 500
        
        # Build questions text
        questions_text = '\n'.join([f"{idx + 1}. [{q.get('skill', '')}] {q.get('question', '')}" 
                                    for idx, q in enumerate(questions)])
        
        # Create assistant configuration for VAPI
        # For REST API creation, we can include maxTokens
        assistant_config_for_api = {
            'model': {
                'provider': 'openai',
                'model': 'gpt-4',
                'messages': [
                    {
                        'role': 'system',
                        'content': system_message
                    },
                    {
                        'role': 'assistant',
                        'content': assistant_message + f'\n\nQuestions to ask:\n{questions_text}'
                    }
                ],
                'temperature': 0.7,
                'maxTokens': 500
            },
            'voice': {
                'provider': '11labs',
                'voiceId': '21m00Tcm4TlvDq8ikWAM'  # Professional voice
            },
            'firstMessage': f"Hello {candidate_name}, thank you for taking the time to interview with us today. I'm excited to learn more about your background and experience. Let's begin!"
        }
        
        # For Web SDK inline config, remove unsupported fields (maxTokens not supported)
        assistant_config_for_web = {
            'model': {
                'provider': 'openai',
                'model': 'gpt-4',
                'messages': [
                    {
                        'role': 'system',
                        'content': system_message
                    },
                    {
                        'role': 'assistant',
                        'content': assistant_message + f'\n\nQuestions to ask:\n{questions_text}'
                    }
                ],
                'temperature': 0.7
            },
            'voice': {
                'provider': '11labs',
                'voiceId': '21m00Tcm4TlvDq8ikWAM'  # Professional voice
            },
            'firstMessage': f"Hello {candidate_name}, thank you for taking the time to interview with us today. I'm excited to learn more about your background and experience. Let's begin!"
        }
        
        # Create assistant via REST API first (recommended for Web SDK)
        # This ensures the assistant is properly configured before starting the call
        try:
            vapi_url = 'https://api.vapi.ai/assistant'
            headers = {
                'Authorization': f'Bearer {vapi_api_key}',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"Creating assistant via VAPI API...")
            response = requests.post(vapi_url, json=assistant_config_for_api, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                assistant_data = response.json()
                assistant_id = assistant_data.get('id')
                logger.info(f"Assistant created successfully with ID: {assistant_id}")
                
                return jsonify({
                    'success': True,
                    'assistantId': assistant_id,
                    'assistant': assistant_config_for_web  # Return Web SDK compatible config as fallback
                })
            else:
                error_text = response.text
                error_details = {}
                try:
                    error_json = response.json()
                    error_text = error_json.get('message', error_json.get('error', error_text))
                    error_details = error_json
                except ValueError:
                    pass
                
                # Check for credit-related errors
                error_lower = error_text.lower() if error_text else ''
                credit_keywords = ['credit', 'balance', 'insufficient', 'payment', 'subscription', 'quota', 'limit exceeded']
                is_credit_error = any(keyword in error_lower for keyword in credit_keywords)
                
                logger.error(f"Failed to create assistant: {response.status_code} - {error_text}")
                logger.error(f"Full error response: {error_details if error_details else response.text}")
                logger.error(f"Assistant config sent: {json.dumps(assistant_config_for_api, indent=2)}")
                
                if is_credit_error:
                    logger.error("⚠️ CREDIT ERROR DETECTED - User may have insufficient VAPI credits")
                    return jsonify({
                        'success': False,
                        'message': f'VAPI credits issue detected: {error_text}. Please check your VAPI account balance at https://dashboard.vapi.ai',
                        'credit_error': True,
                        'error_details': error_details if error_details else None
                    }), 402  # Payment Required status code
                
                # Fallback: return Web SDK compatible config directly
                logger.warning("Falling back to inline assistant config (Web SDK format)")
                return jsonify({
                    'success': True,
                    'assistant': assistant_config_for_web,
                    'warning': f'Assistant creation failed ({response.status_code}): {error_text}. Using inline config.'
                })
        except Exception as api_error:
            logger.error(f"Error creating assistant via API: {str(api_error)}")
            # Fallback: return Web SDK compatible config directly
            logger.warning("Falling back to inline assistant config (Web SDK format)")
            return jsonify({
                'success': True,
                'assistant': assistant_config_for_web
            })
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error getting assistant config: {str(e)}\n{error_traceback}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/mock-interview/start-call', methods=['POST'])
def start_vapi_call():
    """Start a VAPI call for mock interview
    
    NOTE: This endpoint uses VAPI's REST API. You may need to adjust:
    1. API endpoint URLs based on VAPI's current API structure
    2. Request payload structure
    3. Response parsing
    
    Set VAPI_PRIVATE_KEY in your .env file.
    See VAPI_SETUP.md for configuration instructions.
    """
    try:
        import requests
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided in request'
            }), 400
            
        candidate_name = data.get('candidate_name', '')
        job_role = data.get('job_role', '')
        interview_type = data.get('interview_type', 'technical')
        questions = data.get('questions', [])
        system_message = data.get('system_message', '')
        assistant_message = data.get('assistant_message', '')
        phone_number = data.get('phone_number', '')  # Optional: for phone calls
        
        # Get VAPI API key from environment
        vapi_api_key = os.getenv('VAPI_PRIVATE_KEY', '')
        if not vapi_api_key:
            logger.error("VAPI_PRIVATE_KEY not found in environment variables")
            return jsonify({
                'success': False,
                'message': 'VAPI API key not configured. Please set VAPI_PRIVATE_KEY in your .env file. See VAPI_SETUP.md for instructions.'
            }), 500
        
        logger.info(f"Starting VAPI call for candidate: {candidate_name}, role: {job_role}, type: {interview_type}")
        
        # Build questions text
        questions_text = '\n'.join([f"{idx + 1}. [{q.get('skill', '')}] {q.get('question', '')}" 
                                    for idx, q in enumerate(questions)])
        
        # Create assistant configuration
        assistant_config = {
            'model': {
                'provider': 'openai',
                'model': 'gpt-4',
                'messages': [
                    {
                        'role': 'system',
                        'content': system_message
                    },
                    {
                        'role': 'assistant',
                        'content': assistant_message + f'\n\nQuestions to ask:\n{questions_text}'
                    }
                ],
                'temperature': 0.7,
                'maxTokens': 500
            },
            'voice': {
                'provider': '11labs',
                'voiceId': '21m00Tcm4TlvDq8ikWAM'  # Professional voice
            },
            'firstMessage': f"Hello {candidate_name}, thank you for taking the time to interview with us today. I'm excited to learn more about your background and experience. Let's begin!"
        }
        
        # Create phone call via VAPI API
        vapi_url = 'https://api.vapi.ai/call'
        headers = {
            'Authorization': f'Bearer {vapi_api_key}',
            'Content-Type': 'application/json'
        }
        
        # Build payload - VAPI requires either phoneNumberId or phoneNumber
        # Based on error: "Need Either `phoneNumberId` Or `phoneNumber`"
        payload = {
            'assistant': assistant_config
        }
        
        # Get phoneNumberId from environment (for web calls) or use provided phone number
        vapi_phone_number_id = os.getenv('VAPI_PHONE_NUMBER_ID', '')
        
        if phone_number:
            # Use provided phone number (for phone calls)
            payload['customer'] = {
                'number': phone_number
            }
            logger.info(f"Initiating phone call to: {phone_number}")
        elif vapi_phone_number_id:
            # Use phoneNumberId from environment (for web calls)
            # VAPI accepts phoneNumberId in customer object
            payload['customer'] = {
                'phoneNumberId': vapi_phone_number_id
            }
            logger.info(f"Using VAPI phone number ID: {vapi_phone_number_id}")
        else:
            # VAPI requires either phoneNumberId or phoneNumber
            # For web calls, you need to configure a phoneNumberId in VAPI dashboard
            # and add it to .env as VAPI_PHONE_NUMBER_ID
            logger.error("VAPI requires phoneNumberId or phoneNumber. Neither provided.")
            return jsonify({
                'success': False,
                'message': 'VAPI requires either a phone number or phoneNumberId. For web calls, configure VAPI_PHONE_NUMBER_ID in your .env file. See VAPI_SETUP.md for instructions.'
            }), 400
        
        logger.info(f"Making request to VAPI API: {vapi_url}")
        logger.debug(f"Payload structure: assistant configured with {len(questions)} questions")
        
        # For browser-based calls, VAPI might use a different endpoint
        # This is a placeholder - adjust based on VAPI documentation
        try:
            response = requests.post(vapi_url, json=payload, headers=headers, timeout=30)
        except requests.exceptions.Timeout:
            logger.error("VAPI API request timed out")
            return jsonify({
                'success': False,
                'message': 'Request to VAPI API timed out. Please check your internet connection and try again.'
            }), 500
        except requests.exceptions.ConnectionError as e:
            logger.error(f"VAPI API connection error: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to connect to VAPI API: {str(e)}. Please check your internet connection.'
            }), 500
        except requests.exceptions.RequestException as e:
            logger.error(f"VAPI API request error: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error making request to VAPI API: {str(e)}'
            }), 500
        
        if response.status_code == 200 or response.status_code == 201:
            try:
                call_data = response.json()
                return jsonify({
                    'success': True,
                    'call_id': call_data.get('id', ''),
                    'message': 'Call started successfully'
                })
            except ValueError:
                logger.error(f"VAPI API returned invalid JSON: {response.text}")
                return jsonify({
                    'success': False,
                    'message': 'VAPI API returned invalid response format'
                }), 500
        else:
            error_text = response.text
            error_details = {}
            try:
                error_json = response.json()
                error_text = error_json.get('message', error_json.get('error', error_text))
                error_details = error_json
            except ValueError:
                pass
            logger.error(f"VAPI API error: {response.status_code} - {error_text}")
            logger.error(f"Full VAPI response: {error_details if error_details else response.text}")
            return jsonify({
                'success': False,
                'message': f'VAPI API error (status {response.status_code}): {error_text}',
                'details': error_details if error_details else None
            }), 500
            
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error starting VAPI call: {str(e)}\n{error_traceback}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/mock-interview/call-status/<call_id>', methods=['GET'])
def get_call_status(call_id):
    """Get status and conversation history for a VAPI call"""
    try:
        import requests
        
        vapi_api_key = os.getenv('VAPI_PRIVATE_KEY', '')
        if not vapi_api_key:
            return jsonify({
                'success': False,
                'message': 'VAPI API key not configured'
            }), 500
        
        # Get call status from VAPI
        vapi_url = f'https://api.vapi.ai/call/{call_id}'
        headers = {
            'Authorization': f'Bearer {vapi_api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(vapi_url, headers=headers)
        
        if response.status_code == 200:
            call_data = response.json()
            
            # Extract conversation history from call data
            conversation_history = []
            # VAPI stores messages in a specific format - adjust based on actual API response
            messages = call_data.get('messages', [])
            for msg in messages:
                if msg.get('role') and msg.get('content'):
                    conversation_history.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            
            return jsonify({
                'success': True,
                'status': call_data.get('status', 'unknown'),
                'conversation_history': conversation_history
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get call status'
            }), 500
            
    except Exception as e:
        logger.error(f"Error getting call status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/mock-interview/end-call/<call_id>', methods=['POST'])
def end_vapi_call(call_id):
    """End a VAPI call"""
    try:
        import requests
        
        vapi_api_key = os.getenv('VAPI_PRIVATE_KEY', '')
        if not vapi_api_key:
            return jsonify({
                'success': False,
                'message': 'VAPI API key not configured'
            }), 500
        
        # End call via VAPI API
        vapi_url = f'https://api.vapi.ai/call/{call_id}/end'
        headers = {
            'Authorization': f'Bearer {vapi_api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(vapi_url, headers=headers)
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Call ended successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to end call'
            }), 500
            
    except Exception as e:
        logger.error(f"Error ending call: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/mock-interview/vapi-webhook', methods=['POST'])
def vapi_webhook():
    """Handle VAPI webhook events"""
    try:
        data = request.get_json()
        event_type = data.get('type', '')
        
        logger.info(f"VAPI webhook received: {event_type}")
        
        # Handle different VAPI event types
        if event_type == 'function-call':
            # Handle function calls from VAPI
            function_name = data.get('functionCall', {}).get('name', '')
            parameters = data.get('functionCall', {}).get('parameters', {})
            
            if function_name == 'get_next_question':
                # Get next question from database
                job_role = parameters.get('job_role', '')
                interview_type = parameters.get('interview_type', 'technical')
                asked_questions = parameters.get('asked_questions', [])
                
                # Fetch questions
                skills_list = resolve_mock_interview_skills(job_role, parameters.get('skills'))
                if not skills_list:
                    return jsonify({
                        'result': 'No more questions available'
                    })
                
                # Get all available questions
                all_questions = []
                for skill in skills_list:
                    # Get table name based on interview type (dictionary-based, no if-else)
                    table_name = get_question_table_name(interview_type, skill)
                    questions, error = get_questions_from_table(table_name)
                    if not error and questions:
                        for q in questions:
                            all_questions.append({
                                'question': q,
                                'skill': skill
                            })
                
                # Find a question that hasn't been asked
                asked_texts = [q.get('question', '') if isinstance(q, dict) else str(q) for q in asked_questions]
                for q_obj in all_questions:
                    if q_obj['question'] not in asked_texts:
                        return jsonify({
                            'result': q_obj['question']
                        })
                
                return jsonify({
                    'result': 'No more questions available'
                })
        
        # Return success for other event types
        return jsonify({
            'success': True,
            'message': 'Webhook processed'
        })
        
    except Exception as e:
        logger.error(f"VAPI webhook error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing webhook: {str(e)}'
        }), 500

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
        user_message = data.get('message', '').strip()
        context = data.get('context', {})
        conversation_history = data.get('conversationHistory', [])

        # Log received data for debugging
        logger.info(f"Received chatbot request - message: {user_message[:50] if user_message else 'None'}")

        # Validate input
        if not user_message:
            return jsonify({
                'success': False,
                'message': 'Message is required'
            }), 400

        # Pre-check for obvious off-topic questions
        user_message_lower = user_message.lower()
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
        has_interview_context = (
            any(keyword in user_message_lower for keyword in interview_keywords)
            or any(keyword in user_message_lower for keyword in platform_keywords)
            or any(keyword in user_message_lower for keyword in interview_type_keywords)
            or is_ask_ai_question
        )
        
        # If has off-topic keywords but no interview context, redirect immediately
        # BUT skip redirect if this is an "Ask AI" question
        if has_off_topic and not has_interview_context and not is_ask_ai_question:
            redirect_message = "I'm specifically designed to help with interview preparation only. I can assist you with technical interview questions, behavioral interview tips, coding problems, interview strategies, and career preparation. How can I help you prepare for your interview?"
            return jsonify({
                'success': True,
                'response': redirect_message
            })

        # Feedback-specific handling: require the actual feedback text
        if is_feedback_question(user_message):
            feedback_text = extract_feedback_text(user_message)
            if not feedback_text:
                return jsonify({
                    'success': True,
                    'response': build_feedback_missing_response()
                })

        # If user asks about rubric basis and mentions a specific interview type,
        # ensure the rubric context matches that type.
        if is_rubric_question(user_message):
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
                    include_improvement=is_improvement_question(user_message)
                )
            else:
                rubric_reply = build_rubric_response(
                    None,
                    include_improvement=is_improvement_question(user_message),
                    include_all=True
                )
            return jsonify({
                'success': True,
                'response': rubric_reply
            })

        # Build system prompt
        system_prompt = """You are an Interview Preparation Assistant EXCLUSIVELY designed for interview preparation. You MUST NOT answer any questions outside of interview preparation topics.

STRICT RULES - YOU MUST FOLLOW THESE:
1. ONLY answer questions about:
   - Technical interview preparation (coding, algorithms, data structures, system design)
   - Behavioral interview preparation (STAR method, common questions, examples)
   - Interview strategies and tips
   - Career preparation related to interviews
   - Coding problems and solutions for interview practice
   - Interview-related concepts and explanations
   - Platform interview types, job roles, and skills listed in "Platform Skills"
   - If the question is about platform skills/roles/interview types or interview feedback, answer it even if "interview" is not mentioned.

2. DO NOT answer questions about:
   - Movies, entertainment, TV shows, celebrities
   - General knowledge, history, geography, science (unless directly related to interview prep)
   - Cooking, recipes, food
   - Travel, vacation planning
   - Personal relationships, dating advice
   - Current events, news, politics (unless related to job market/interviews)
   - Sports, games, hobbies (unless related to interview preparation)
   - Any topic NOT directly related to interview preparation

3. When user asks off-topic questions, you MUST:
   - DO NOT provide any answer or information about the off-topic question
   - IMMEDIATELY redirect with this EXACT response: "I'm specifically designed to help with interview preparation only. I can assist you with technical interview questions, behavioral interview tips, coding problems, interview strategies, and career preparation. How can I help you prepare for your interview?"
   - DO NOT explain why you can't answer, just redirect politely

4. Examples of what to REJECT:
   - "Tell me about movies" → Redirect immediately
   - "What's the weather?" → Redirect immediately
   - "Explain quantum physics" → Redirect (unless asked in context of interview prep)
   - "How to cook pasta?" → Redirect immediately
   - "Best travel destinations" → Redirect immediately

5. Examples of what to ACCEPT:
   - "How to answer 'Tell me about yourself' in interview?" → Answer
   - "Explain binary search algorithm" → Answer (interview prep context)
   - "STAR method examples" → Answer
   - "Coding interview tips" → Answer
   - "System design interview questions" → Answer

6. Feedback questions (Skill Prep or mock interview):
   - If the user asks any question about feedback they received, you MUST answer clearly and directly.
   - Base your response ONLY on the specific feedback provided in the conversation history or the user's message.
   - Do NOT add generic or unrelated advice.
   - Explain what the feedback means, and guide what it implies for their performance or improvement.
   - If the specific feedback is not present, ask the user to share it. Do NOT guess.

7. Rubric-based evaluation questions:
   - If the user asks how Skill Prep or mock interview evaluation works, clearly explain the rubric basis.
   - Use the "Rubric Basis" provided in the context info to list the exact criteria and weights.
   - When asked how to improve, tie suggestions back to these rubric criteria.
   - Keep the response specific to the user's interview type and skill context.
8. Platform interview tips:
   - If the user asks for interview tips or guidance, keep it within the platform skills listed in "Platform Skills".
   - If a tip request is outside those skills or not interview-related, redirect with the standard off-topic message.

Your role is to provide clear, helpful, and actionable guidance ONLY on interview preparation topics.

If the user asks about a specific question they're practicing, provide targeted help for that question.

CRITICAL: Never provide answers to off-topic questions. Always redirect immediately with the standard message above."""

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
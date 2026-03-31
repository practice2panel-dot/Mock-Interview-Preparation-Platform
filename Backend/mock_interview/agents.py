"""
CrewAI agents for the mock interview application.
"""
from crewai import Agent, Task, Crew, LLM
from langchain_openai import ChatOpenAI
from typing import List, Dict
import random
import os
from mock_interview.config import JOB_ROLE_SKILLS, OPENAI_API_KEY

# Ensure API key is loaded from environment
if not OPENAI_API_KEY or OPENAI_API_KEY == "your-api-key-here":
    # Try loading directly from .env file
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path, override=True)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your-api-key-here":
        raise ValueError("OPENAI_API_KEY not found or is placeholder. Please set it in backend/.env file")

MODEL_NAME = os.getenv("MOCK_INTERVIEW_MODEL", "gpt-4o-mini")
MAX_TOKENS = int(os.getenv("MOCK_INTERVIEW_MAX_TOKENS", "700"))

# Initialize CrewAI LLM (CrewAI expects its own LLM wrapper or a model string)
llm = LLM(
    model=MODEL_NAME,
    api_key=OPENAI_API_KEY,
    temperature=0.7,
    max_tokens=MAX_TOKENS
)

class QuestionAgent:
    """Generates interview questions based on job role and interview type."""
    
    @staticmethod
    def generate_questions(job_role: str, interview_type: str, num_questions: int = 5) -> List[str]:
        """Generate role and type-specific interview questions."""
        skills = ", ".join(JOB_ROLE_SKILLS.get(job_role, []))
        
        if interview_type.lower() == "behavioral":
            prompt = f"""Generate {num_questions} behavioral interview questions using the STAR (Situation, Task, Action, Result) framework.
            
Requirements:
- Questions should be general and applicable to all professions (NOT job-specific)
- Focus on soft skills: teamwork, adaptability, leadership, communication, problem-solving
- Questions should prompt candidates to share real-life work experiences
- Use the STAR framework structure (Situation, Task, Action, Result)
- Make questions realistic and engaging
- Examples of good questions:
  * "Tell me about a time you had to deal with a difficult teammate."
  * "Describe a challenge you faced and how you overcame it."
  * "Share an example of when you had to manage pressure under a tight deadline."
  * "Tell me about a time you took initiative to solve a problem."
  * "Describe a situation where you learned from a mistake."
- Return only the questions, one per line, numbered 1-{num_questions}
- Do not include explanations or answers"""
        else:
            prompt = f"""Generate {num_questions} {interview_type.lower()} interview questions for a {job_role} skilled in {skills}.
        
Requirements:
- Questions should be specific to the {job_role} role and {interview_type} interview type
- Questions should test knowledge and understanding of: {skills}
- Make questions realistic and challenging
- Return only the questions, one per line, numbered 1-{num_questions}
- Do not include explanations or answers"""
        
        agent = Agent(
            role="Interview Question Generator",
            goal="Generate relevant, challenging interview questions",
            backstory="You are an expert at creating interview questions that effectively assess candidates' knowledge and skills.",
            llm=llm,
            verbose=False
        )
        
        task = Task(
            description=prompt,
            agent=agent,
            expected_output=f"A list of {num_questions} interview questions, one per line, numbered 1-{num_questions}"
        )
        
        # Execute using Crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=False
        )
        result = crew.kickoff()
        
        # Convert result to string if needed
        result_str = str(result) if not isinstance(result, str) else result
        
        # Parse questions from result
        questions = []
        for line in result_str.strip().split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering/bullets
                question = line.split('.', 1)[-1].strip().lstrip('- ').strip()
                if question:
                    questions.append(question)
        
        # If parsing didn't work well, use OpenAI directly
        if len(questions) < num_questions:
            from langchain_openai import ChatOpenAI
            from langchain.schema import HumanMessage
            
            chat = ChatOpenAI(model=MODEL_NAME, temperature=0.7, api_key=OPENAI_API_KEY, max_tokens=MAX_TOKENS)
            response = chat.invoke([HumanMessage(content=prompt)])
            result = response.content
            
            questions = []
            for line in result.strip().split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    question = line.split('.', 1)[-1].strip().lstrip('- ').lstrip('• ').strip()
                    if question and len(question) > 10:
                        questions.append(question)
            
            # If still not enough, take first num_questions
            questions = questions[:num_questions]
        
        return questions[:num_questions] if questions else [
            f"Tell me about your experience with {skill}" 
            for skill in JOB_ROLE_SKILLS.get(job_role, [])[:num_questions]
        ]


class EvaluatorAgent:
    """Evaluates candidate answers and provides feedback."""
    
    @staticmethod
    def evaluate_answer(question: str, answer: str, job_role: str, interview_type: str) -> Dict:
        """Evaluate an answer and return short feedback + detailed rubric."""
        skills = ", ".join(JOB_ROLE_SKILLS.get(job_role, []))
        
        if interview_type.lower() == "behavioral":
            prompt = f"""Evaluate the following behavioral interview answer using the STAR (Situation, Task, Action, Result) framework.

Question: {question}
Candidate Answer: {answer}

Provide:
1. A SHORT 2-line feedback (immediate response) - MUST be exactly 2 lines
2. A DETAILED rubric evaluation with scores on:
   - Situation Clarity (1-10) - How well did the candidate describe the context/situation?
   - Task Definition (1-10) - How clearly did they explain their role and responsibilities?
   - Action Effectiveness (1-10) - How well did they describe the specific actions they took?
   - Result Impact (1-10) - How well did they explain the outcomes and impact?
   - Communication Skill (1-10) - How clear and structured was their communication?

IMPORTANT GUIDELINES:
- The SHORT_FEEDBACK must be exactly 2 lines
- Do NOT start with "The candidate provided" or similar phrases
- Write feedback directly addressing the answer quality, insights, or areas for improvement
- Be concise, constructive, and conversational
- Use natural language that flows well
- Focus on STAR framework elements: Situation, Task, Action, Result
- CRITICAL: If the answer is IRRELEVANT to the question (doesn't address the question, is off-topic), the SHORT_FEEDBACK MUST explicitly ask the candidate to provide a relevant answer that addresses the question

Format your response as:
SHORT_FEEDBACK: [exactly 2 lines of feedback]
DETAILED_EVALUATION:
Situation Clarity: [score]/10 - [brief explanation]
Task Definition: [score]/10 - [brief explanation]
Action Effectiveness: [score]/10 - [brief explanation]
Result Impact: [score]/10 - [brief explanation]
Communication Skill: [score]/10 - [brief explanation]
ADDITIONAL_NOTES: [any additional observations]"""
        else:
            prompt = f"""Evaluate the following interview answer for a {job_role} position ({interview_type} interview).

Question: {question}
Candidate Answer: {answer}
Required Skills: {skills}

Provide:
1. A SHORT 2-line feedback (immediate response) - MUST be exactly 2 lines
2. A DETAILED rubric evaluation with scores on:
   - Technical Accuracy (1-10)
   - Clarity of Communication (1-10)
   - Depth of Understanding (1-10)
   - Relevance to Role (1-10)
   - Overall Quality (1-10)

IMPORTANT GUIDELINES:
- The SHORT_FEEDBACK must be exactly 2 lines
- Do NOT start with "The candidate provided" or similar phrases
- Write feedback directly addressing the answer quality, insights, or areas for improvement
- Be concise, constructive, and conversational
- Use natural language that flows well
- CRITICAL: If the answer is IRRELEVANT to the question (doesn't address the question, is off-topic, or unrelated to the role), the SHORT_FEEDBACK MUST explicitly ask the candidate to provide a relevant answer that addresses the question

Format your response as:
SHORT_FEEDBACK: [exactly 2 lines of feedback]
DETAILED_EVALUATION:
Technical Accuracy: [score]/10 - [brief explanation]
Clarity of Communication: [score]/10 - [brief explanation]
Depth of Understanding: [score]/10 - [brief explanation]
Relevance to Role: [score]/10 - [brief explanation]
Overall Quality: [score]/10 - [brief explanation]
ADDITIONAL_NOTES: [any additional observations]"""
        
        if interview_type.lower() == "behavioral":
            agent_backstory = "You are an experienced behavioral interviewer who evaluates answers using the STAR framework. Always write feedback in exactly 2 lines, directly addressing the answer without starting with phrases like 'The candidate provided'. Be conversational, warm, and natural. Focus on how well the candidate structured their response using Situation, Task, Action, and Result."
            expected_output = "A formatted response with SHORT_FEEDBACK (exactly 2 lines, not starting with 'The candidate provided'), DETAILED_EVALUATION with STAR rubric scores (Situation Clarity, Task Definition, Action Effectiveness, Result Impact, Communication Skill), and ADDITIONAL_NOTES"
        else:
            agent_backstory = "You are an experienced technical interviewer who provides balanced, helpful feedback. Always write feedback in exactly 2 lines, directly addressing the answer without starting with phrases like 'The candidate provided'. Be conversational and natural."
            expected_output = "A formatted response with SHORT_FEEDBACK (exactly 2 lines, not starting with 'The candidate provided'), DETAILED_EVALUATION with rubric scores (Technical Accuracy, Clarity, Depth, Relevance, Overall Quality), and ADDITIONAL_NOTES"
        
        agent = Agent(
            role="Interview Evaluator",
            goal="Provide fair, constructive feedback on candidate answers",
            backstory=agent_backstory,
            llm=llm,
            verbose=False
        )
        
        task = Task(
            description=prompt,
            agent=agent,
            expected_output=expected_output
        )
        
        # Execute using Crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=False
        )
        result = crew.kickoff()
        
        # Convert result to string if needed
        result_str = str(result) if not isinstance(result, str) else result
        
        # Parse the result
        short_feedback = ""
        detailed_eval = {}
        additional_notes = ""
        
        lines = result_str.split('\n')
        current_section = None
        feedback_lines = []
        in_feedback = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('SHORT_FEEDBACK:'):
                # Extract first line of feedback
                first_line = line.split(':', 1)[-1].strip()
                if first_line:
                    feedback_lines.append(first_line)
                in_feedback = True
                # Look for next line (should be second line of feedback)
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.startswith('DETAILED_EVALUATION:'):
                        feedback_lines.append(next_line)
                        in_feedback = False
            elif in_feedback and line and not line.startswith('DETAILED_EVALUATION:'):
                # Collect second line of feedback if not already collected
                if len(feedback_lines) < 2:
                    feedback_lines.append(line)
                    in_feedback = False
            elif line.startswith('DETAILED_EVALUATION:'):
                current_section = 'detailed'
                in_feedback = False
            elif line.startswith('ADDITIONAL_NOTES:'):
                current_section = 'notes'
                additional_notes = line.split(':', 1)[-1].strip()
                in_feedback = False
            elif current_section == 'detailed' and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    metric = parts[0].strip()
                    value = parts[1].strip()
                    detailed_eval[metric] = value
            elif current_section == 'notes' and line:
                additional_notes += " " + line
        
        # Join feedback lines (ensure exactly 2 lines)
        if feedback_lines:
            if len(feedback_lines) == 1:
                # If only one line, split it or add a second line
                short_feedback = feedback_lines[0]
            else:
                short_feedback = "\n".join(feedback_lines[:2])  # Take first 2 lines
        else:
            short_feedback = ""
        
        # Fallback: use OpenAI directly if parsing fails
        if not short_feedback:
            from langchain_openai import ChatOpenAI
            from langchain.schema import HumanMessage
            
            chat = ChatOpenAI(model=MODEL_NAME, temperature=0.7, api_key=OPENAI_API_KEY, max_tokens=MAX_TOKENS)
            response = chat.invoke([HumanMessage(content=prompt)])
            result = response.content
            
            # Simple extraction - ensure 2 lines
            if 'SHORT_FEEDBACK:' in result:
                feedback_text = result.split('SHORT_FEEDBACK:')[1].split('DETAILED_EVALUATION:')[0].strip()
                # Split into lines and take first 2
                feedback_lines = [line.strip() for line in feedback_text.split('\n') if line.strip()]
                if len(feedback_lines) >= 2:
                    short_feedback = "\n".join(feedback_lines[:2])
                elif len(feedback_lines) == 1:
                    # If only one line, use it as is (AI should provide 2 lines)
                    short_feedback = feedback_lines[0]
                else:
                    short_feedback = feedback_text[:200]  # Fallback
            else:
                # Extract first 2 meaningful lines
                all_lines = [line.strip() for line in result.split('\n') if line.strip()][:2]
                short_feedback = "\n".join(all_lines) if all_lines else result[:200]
            
            # Extract scores based on interview type
            if interview_type.lower() == "behavioral":
                metrics = ['Situation Clarity', 'Task Definition', 'Action Effectiveness', 
                          'Result Impact', 'Communication Skill']
            else:
                metrics = ['Technical Accuracy', 'Clarity of Communication', 'Depth of Understanding', 
                          'Relevance to Role', 'Overall Quality']
            
            for metric in metrics:
                if metric in result:
                    try:
                        metric_line = [l for l in result.split('\n') if metric in l][0]
                        detailed_eval[metric] = metric_line.split(':', 1)[-1].strip()
                    except:
                        detailed_eval[metric] = "N/A"
        
        # Default values if parsing completely failed - ensure 2 lines
        if not short_feedback:
            short_feedback = "Thank you for your answer.\nLet's continue with the next question."
        
        # Ensure feedback is exactly 2 lines (split if needed, pad if needed)
        feedback_lines = [line.strip() for line in short_feedback.split('\n') if line.strip()]
        if len(feedback_lines) == 1:
            # If only one line, add a second line
            short_feedback = f"{feedback_lines[0]}\nLet's continue."
        elif len(feedback_lines) > 2:
            # If more than 2 lines, take first 2
            short_feedback = "\n".join(feedback_lines[:2])
        else:
            # Already 2 lines, join them
            short_feedback = "\n".join(feedback_lines)
        
        # Ensure we store the string version, not the CrewOutput object
        # If fallback was used, result is already a string (response.content)
        # Otherwise, use result_str which was converted from CrewOutput
        # Always ensure we have a string, not a CrewOutput object
        if isinstance(result, str):
            # Fallback path was used, result is already a string
            detailed_evaluation_text = result
        else:
            # CrewOutput object, use the string version we created
            detailed_evaluation_text = result_str
        
        # Check if answer is irrelevant based on "Relevance to Role" score
        is_irrelevant = False
        relevance_score = None
        
        # Try to extract relevance score from detailed_eval
        if "Relevance to Role" in detailed_eval:
            relevance_str = detailed_eval["Relevance to Role"]
            try:
                # Extract numeric score (e.g., "3/10 - explanation" -> 3)
                score_part = relevance_str.split('/')[0].strip()
                relevance_score = float(score_part)
                # Consider answer irrelevant if relevance score is 4 or below
                if relevance_score <= 4:
                    is_irrelevant = True
            except (ValueError, IndexError):
                # If parsing fails, check if the explanation contains keywords indicating irrelevance
                relevance_lower = relevance_str.lower()
                if any(keyword in relevance_lower for keyword in ["irrelevant", "not relevant", "off-topic", "unrelated", "doesn't address", "does not address"]):
                    is_irrelevant = True
        
        # Also check the detailed evaluation text for irrelevance indicators if score check didn't find it
        if not is_irrelevant:
            # Check detailed_evaluation_text for keywords indicating irrelevance
            detailed_eval_lower = detailed_evaluation_text.lower() if isinstance(detailed_evaluation_text, str) else ""
            if any(keyword in detailed_eval_lower for keyword in ["irrelevant", "not relevant", "off-topic", "unrelated", "doesn't address the question", "does not address the question"]):
                # Also check if relevance score is mentioned as low
                if "relevance" in detailed_eval_lower and any(phrase in detailed_eval_lower for phrase in ["low relevance", "poor relevance", "lack of relevance"]):
                    is_irrelevant = True
        
        # If answer is irrelevant, modify feedback to explicitly ask for a relevant answer
        if is_irrelevant:
            feedback_lines = [line.strip() for line in short_feedback.split('\n') if line.strip()]
            # Modify feedback to ask for relevant answer
            if len(feedback_lines) >= 1:
                # Keep first line if it's meaningful, otherwise replace
                first_line = feedback_lines[0] if feedback_lines[0] and len(feedback_lines[0]) > 20 else "I notice your answer doesn't directly address the question."
                second_line = "Please provide a relevant answer that specifically addresses what was asked."
                short_feedback = f"{first_line}\n{second_line}"
            else:
                short_feedback = "I notice your answer doesn't directly address the question.\nPlease provide a relevant answer that specifically addresses what was asked."
        
        return {
            "short_feedback": short_feedback,
            "detailed_evaluation": detailed_evaluation_text,  # Store full text as string
            "rubric_scores": detailed_eval,
            "is_irrelevant": is_irrelevant  # Add flag for tracking
        }


class FollowUpAgent:
    """Generates follow-up questions based on candidate answers."""
    
    @staticmethod
    def generate_follow_ups(question: str, answer: str, job_role: str, interview_type: str) -> List[str]:
        """Generate 1-3 follow-up questions based on the candidate's answer."""
        num_followups = random.randint(1, 2)  # 1-2 follow-ups for behavioral interviews
        skills = ", ".join(JOB_ROLE_SKILLS.get(job_role, []))
        
        if interview_type.lower() == "behavioral":
            prompt = f"""Based on the following behavioral interview interaction, generate {num_followups} natural, conversational follow-up question(s) that probe deeper into the candidate's STAR response.

Original Question: {question}
Candidate Answer: {answer}

Requirements:
- Questions should be context-aware and build naturally on the candidate's answer
- Focus on STAR framework elements: probe for more details about Situation, Task, Action, or Result
- Use natural, conversational language (not robotic)
- Examples of good follow-ups:
  * "What specific steps did you take in that situation?"
  * "How did your team respond?"
  * "What was the outcome of that approach?"
  * "Can you tell me more about the challenges you faced?"
- Do NOT repeat the original question
- Make them specific and relevant to what the candidate shared
- Return only the questions, one per line, numbered 1-{num_followups}"""
        else:
            prompt = f"""Based on the following interview interaction, generate {num_followups} follow-up question(s) that probe deeper or clarify the candidate's response.

Original Question: {question}
Candidate Answer: {answer}
Job Role: {job_role} ({interview_type} interview)
Required Skills: {skills}

Requirements:
- Questions should be context-aware and build on the candidate's answer
- They should probe for clarification, deeper understanding, or extension
- Do NOT repeat the original question
- Make them specific and relevant
- Return only the questions, one per line, numbered 1-{num_followups}"""
        
        agent = Agent(
            role="Follow-up Question Generator",
            goal="Generate insightful follow-up questions that probe deeper",
            backstory="You excel at asking follow-up questions that reveal deeper understanding and clarify candidate responses.",
            llm=llm,
            verbose=False
        )
        
        task = Task(
            description=prompt,
            agent=agent,
            expected_output=f"A list of {num_followups} follow-up questions, one per line, numbered 1-{num_followups}, that probe deeper into the candidate's answer"
        )
        
        # Execute using Crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=False
        )
        result = crew.kickoff()
        
        # Convert result to string if needed
        result_str = str(result) if not isinstance(result, str) else result
        
        # Parse follow-ups
        follow_ups = []
        for line in result_str.strip().split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                question = line.split('.', 1)[-1].strip().lstrip('- ').lstrip('• ').strip()
                if question and len(question) > 10:
                    follow_ups.append(question)
        
        # Fallback: use OpenAI directly
        if len(follow_ups) < num_followups:
            from langchain_openai import ChatOpenAI
            from langchain.schema import HumanMessage
            
            chat = ChatOpenAI(model=MODEL_NAME, temperature=0.7, api_key=OPENAI_API_KEY, max_tokens=MAX_TOKENS)
            response = chat.invoke([HumanMessage(content=prompt)])
            result = response.content
            
            follow_ups = []
            for line in result.strip().split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    question = line.split('.', 1)[-1].strip().lstrip('- ').lstrip('• ').strip()
                    if question and len(question) > 10:
                        follow_ups.append(question)
        
        return follow_ups[:num_followups] if follow_ups else []


class HintAgent:
    """Provides hints when requested."""
    
    @staticmethod
    def provide_hint(question: str, job_role: str, interview_type: str) -> str:
        """Generate a concise, guiding hint without revealing the full solution."""
        skills = ", ".join(JOB_ROLE_SKILLS.get(job_role, []))
        
        if interview_type.lower() == "behavioral":
            prompt = f"""Provide a short, guiding hint for the following behavioral interview question using the STAR framework. Do NOT reveal the full answer or solution.

Question: {question}

Requirements:
- Keep it concise (1-2 sentences)
- Guide the candidate to use the STAR framework (Situation, Task, Action, Result)
- Suggest they recall a specific experience and structure it clearly
- Be encouraging and supportive
- Example: Try recalling a specific experience - start by describing the situation first, then your role, actions, and final outcome."""
        else:
            prompt = f"""Provide a short, guiding hint for the following interview question. Do NOT reveal the full answer or solution.

Question: {question}
Job Role: {job_role} ({interview_type} interview)
Required Skills: {skills}

Requirements:
- Keep it concise (1-2 sentences)
- Provide guidance without spoiling the answer
- Help the candidate think in the right direction
- Be encouraging and supportive"""
        
        agent = Agent(
            role="Hint Provider",
            goal="Provide helpful hints without revealing answers",
            backstory="You are skilled at guiding candidates with subtle hints that help them think without giving away the solution.",
            llm=llm,
            verbose=False
        )
        
        task = Task(
            description=prompt,
            agent=agent,
            expected_output="A short, concise hint (1-2 sentences) that guides the candidate without revealing the full answer"
        )
        
        # Execute using Crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=False
        )
        result = crew.kickoff()
        
        # Convert result to string if needed
        result_str = str(result) if not isinstance(result, str) else result
        
        # Clean up the result
        hint = result_str.strip()
        if len(hint) > 300:
            hint = hint[:300] + "..."
        
        return hint


class IntentDetectorAgent:
    """Detects user intent from natural language input."""
    
    @staticmethod
    def detect_intent(user_input: str, current_question: str = "", conversation_state: str = "") -> str:
        """
        Detect user intent from natural language input.
        Returns: "repeat_question", "hint_request", "need_time", or "normal_answer"
        """
        if not user_input:
            return "normal_answer"
        
        prompt = f"""Analyze the following user input from an interview candidate and determine their intent.
The current question is: {current_question}

User input: "{user_input}"

Determine the user's intent based on the natural language meaning, not keywords. Classify as one of:
- "repeat_question": User wants to hear the question again, is confused, didn't catch it, or asks for clarification
- "hint_request": User is unsure, asking for help, expressing difficulty, or needs guidance
- "need_time": User wants to pause, needs time to think, or is hesitating
- "normal_answer": User is providing an actual answer to the question

Examples:
- "Sorry, I didn't catch that" → repeat_question
- "What did you say again?" → repeat_question
- "Can you repeat that?" → repeat_question
- "I'm not sure" → hint_request
- "This is hard" → hint_request
- "Can you help me?" → hint_request
- "Give me a moment" → need_time
- "Let me think" → need_time
- "Hold on" → need_time

Respond with ONLY one word: repeat_question, hint_request, need_time, or normal_answer"""
        
        agent = Agent(
            role="Intent Classifier",
            goal="Accurately classify user intent from natural language",
            backstory="You are an expert at understanding conversational intent and user needs from context.",
            llm=llm,
            verbose=False
        )
        
        task = Task(
            description=prompt,
            agent=agent,
            expected_output="One word: repeat_question, hint_request, need_time, or normal_answer"
        )
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=False
        )
        
        try:
            result = crew.kickoff()
            result_str = str(result).strip().lower()
            
            # Validate and return intent
            valid_intents = ["repeat_question", "hint_request", "need_time", "normal_answer"]
            for intent in valid_intents:
                if intent in result_str:
                    return intent
            
            # Fallback: use OpenAI directly if CrewAI parsing fails
            from langchain_openai import ChatOpenAI
            from langchain.schema import HumanMessage
            
            chat = ChatOpenAI(model=MODEL_NAME, temperature=0.3, api_key=OPENAI_API_KEY, max_tokens=MAX_TOKENS)
            response = chat.invoke([HumanMessage(content=prompt)])
            result_str = response.content.strip().lower()
            
            for intent in valid_intents:
                if intent in result_str:
                    return intent
            
            # Default to normal_answer if unclear
            return "normal_answer"
            
        except Exception as e:
            print(f"Intent detection error: {e}")
            # Fallback logic based on simple heuristics if AI fails
            user_lower = user_input.lower()
            if any(phrase in user_lower for phrase in ["repeat", "again", "didn't catch", "didn't hear", "what did you say", "say that"]):
                return "repeat_question"
            elif any(phrase in user_lower for phrase in ["hint", "help", "not sure", "unsure", "hard", "difficult", "stuck"]):
                return "hint_request"
            elif any(phrase in user_lower for phrase in ["wait", "hold on", "give me", "moment", "think", "pause"]):
                return "need_time"
            return "normal_answer"


class ImprovementAgent:
    """Generates areas of improvement based on interview performance."""
    
    @staticmethod
    def generate_improvements(evaluations: List[Dict], job_role: str, interview_type: str) -> Dict[str, str]:
        """Generate areas of improvement for Communication, Knowledge Accuracy, and Clarity."""
        # Collect all feedback and scores
        all_feedback = []
        all_scores = {
            "Communication": [],
            "Knowledge Accuracy": [],
            "Clarity": []
        }
        
        # Map metrics to improvement categories based on interview type
        if interview_type.lower() == "behavioral":
            metric_mapping = {
                "Communication Skill": "Communication",
                "Situation Clarity": "Clarity",
                "Task Definition": "Clarity",
                "Action Effectiveness": "Knowledge Accuracy",
                "Result Impact": "Knowledge Accuracy"
            }
        else:
            metric_mapping = {
                "Clarity of Communication": "Communication",
                "Technical Accuracy": "Knowledge Accuracy",
                "Depth of Understanding": "Clarity"
            }
        
        for eval_data in evaluations:
            evaluation = eval_data.get("evaluation", {})
            rubric_scores = evaluation.get("rubric_scores", {})
            detailed_eval = evaluation.get("detailed_evaluation", "")
            short_feedback = evaluation.get("short_feedback", "")
            
            all_feedback.append(f"Feedback: {short_feedback}\nDetailed: {detailed_eval}")
            
            # Extract scores for each category
            for metric, category in metric_mapping.items():
                if metric in rubric_scores:
                    score_str = rubric_scores[metric]
                    try:
                        score = float(score_str.split('/')[0].strip())
                        all_scores[category].append(score)
                    except:
                        pass
        
        # Calculate average scores
        avg_scores = {}
        for category, scores in all_scores.items():
            if scores:
                avg_scores[category] = round(sum(scores) / len(scores), 1)
            else:
                avg_scores[category] = 0.0
        
        # Generate improvements using AI
        feedback_text = "\n\n".join(all_feedback[:5])  # Limit to first 5 for context
        
        if interview_type.lower() == "behavioral":
            rubric_guidance = """COMMUNICATION GUIDANCE:
- **Incorporate Examples**: When discussing concepts, include specific examples tied to real projects or experiences.
- **Practice Active Listening**: Confirm understanding of the question before answering to stay aligned and engaged.
- **Use Structured Responses**: Organize answers with clear frameworks (e.g., STAR) so your points remain coherent.

KNOWLEDGE ACCURACY GUIDANCE (STAR Framework):
- **Describe Situation Clearly**: Start by setting the context - when, where, and what was happening.
- **Define Your Task**: Clearly explain your role and responsibilities in that situation.
- **Detail Your Actions**: Be specific about the steps you took - what did you actually do?
- **Highlight Results**: Quantify outcomes when possible - what was the impact? What did you learn?

CLARITY GUIDANCE:
- **Organize Ideas Before Speaking**: Take a breath to outline your answer mentally before responding.
- **Use Signposting Language**: Guide the interviewer through your answer with cues like "First… Next… Finally…".
- **Summarize Key Points**: End answers with a brief recap to reinforce your main message."""
        else:
            rubric_guidance = """COMMUNICATION GUIDANCE:
- **Incorporate Examples**: When discussing concepts, include specific examples tied to real projects or experiences.
- **Practice Active Listening**: Confirm understanding of the question before answering to stay aligned and engaged.
- **Use Structured Responses**: Organize answers with clear frameworks (e.g., STAR) so your points remain coherent.

KNOWLEDGE ACCURACY GUIDANCE:
- **Deepen Technical Knowledge**: Review core fundamentals (e.g., backpropagation, architectures, tuning) to articulate them accurately.
- **Stay Updated**: Follow current research, articles, and industry advances so your answers reflect up-to-date knowledge.
- **Practice Problem-Solving**: Work through coding challenges or case studies to sharpen accuracy under interview conditions.

CLARITY GUIDANCE:
- **Organize Ideas Before Speaking**: Take a breath to outline your answer mentally before responding.
- **Use Signposting Language**: Guide the interviewer through your answer with cues like "First… Next… Finally…".
- **Summarize Key Points**: End answers with a brief recap to reinforce your main message."""
        
        prompt = f"""Based on the following interview evaluations for a {job_role} position ({interview_type} interview), provide specific areas of improvement for each focus area. You must prioritise the rubric guidance provided below when crafting suggestions.

RUBRIC TO FOLLOW:
{rubric_guidance}

INTERVIEW FEEDBACK SUMMARY:
{feedback_text}

AVERAGE SCORES (OUT OF 10):
- Communication: {avg_scores.get('Communication', 0)}/10
- Knowledge Accuracy: {avg_scores.get('Knowledge Accuracy', 0)}/10
- Clarity: {avg_scores.get('Clarity', 0)}/10

INSTRUCTIONS:
- Give 2-3 actionable suggestions per focus area.
- Each suggestion MUST begin with "- **Key Phrase**:" where the bold phrase clearly names the improvement (e.g., "- **Incorporate Examples**: ...").
- Keep the tone constructive and specific, referencing interview observations when helpful.

FORMAT YOUR RESPONSE EXACTLY AS:
COMMUNICATION_IMPROVEMENTS:
- **Key Phrase**: suggestion text
- **Key Phrase**: suggestion text

KNOWLEDGE_ACCURACY_IMPROVEMENTS:
- **Key Phrase**: suggestion text
- **Key Phrase**: suggestion text

CLARITY_IMPROVEMENTS:
- **Key Phrase**: suggestion text
- **Key Phrase**: suggestion text"""
        
        agent = Agent(
            role="Interview Improvement Advisor",
            goal="Provide specific, actionable improvement suggestions",
            backstory="You are an expert career coach who provides constructive, specific feedback to help candidates improve their interview performance.",
            llm=llm,
            verbose=False
        )
        
        task = Task(
            description=prompt,
            agent=agent,
            expected_output="A formatted response with improvement suggestions for Communication, Knowledge Accuracy, and Clarity"
        )
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=False
        )
        
        try:
            result = crew.kickoff()
            result_str = str(result) if not isinstance(result, str) else result
            
            # Parse improvements
            improvements = {
                "Communication": "",
                "Knowledge Accuracy": "",
                "Clarity": ""
            }
            
            lines = result_str.split('\n')
            current_category = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('COMMUNICATION_IMPROVEMENTS:'):
                    current_category = "Communication"
                    content = line.split(':', 1)[-1].strip()
                    if content:
                        improvements["Communication"] = content
                elif line.startswith('KNOWLEDGE_ACCURACY_IMPROVEMENTS:'):
                    current_category = "Knowledge Accuracy"
                    content = line.split(':', 1)[-1].strip()
                    if content:
                        improvements["Knowledge Accuracy"] = content
                elif line.startswith('CLARITY_IMPROVEMENTS:'):
                    current_category = "Clarity"
                    content = line.split(':', 1)[-1].strip()
                    if content:
                        improvements["Clarity"] = content
                elif current_category and line:
                    # Continue adding to current category
                    if improvements[current_category]:
                        improvements[current_category] += "\n" + line
                    else:
                        improvements[current_category] = line
            
            # Fallback: use OpenAI directly if parsing fails
            if not any(improvements.values()):
                from langchain_openai import ChatOpenAI
                from langchain.schema import HumanMessage
                
                chat = ChatOpenAI(model=MODEL_NAME, temperature=0.7, api_key=OPENAI_API_KEY, max_tokens=MAX_TOKENS)
                response = chat.invoke([HumanMessage(content=prompt)])
                result_str = response.content
                
                # Simple extraction
                for category in improvements.keys():
                    category_upper = category.upper().replace(' ', '_')
                    if f"{category_upper}_IMPROVEMENTS:" in result_str:
                        start_idx = result_str.find(f"{category_upper}_IMPROVEMENTS:") + len(f"{category_upper}_IMPROVEMENTS:")
                        # Find next category or end
                        next_categories = [f"{c.upper().replace(' ', '_')}_IMPROVEMENTS:" for c in improvements.keys() if c != category]
                        end_idx = len(result_str)
                        for next_cat in next_categories:
                            if next_cat in result_str:
                                idx = result_str.find(next_cat, start_idx)
                                if idx != -1:
                                    end_idx = min(end_idx, idx)
                        improvements[category] = result_str[start_idx:end_idx].strip()
            
            # Ensure we have content for each category
            for category in improvements.keys():
                if not improvements[category]:
                    improvements[category] = ""
                lines = []
                for raw_line in improvements[category].split('\n'):
                    line = raw_line.strip()
                    if not line:
                        continue
                    if not line.startswith('-'):
                        line = f"- {line}"
                    if '**' not in line:
                        if ':' in line:
                            prefix, rest = line.split(':', 1)
                            prefix_clean = prefix.lstrip('- ').strip()
                            line = f"- **{prefix_clean}**:{rest}" if rest else f"- **{prefix_clean}**"
                        else:
                            content = line.lstrip('- ').strip()
                            line = f"- **{content}**"
                    lines.append(line)
                if lines:
                    improvements[category] = "\n".join(lines)
                else:
                    improvements[category] = "- **Focus Area**: Continue strengthening this skill based on the interview feedback."
            
            return improvements
            
        except Exception as e:
            print(f"Error generating improvements: {e}")
            # Return default improvements
            return {
                "Communication": "- **Incorporate Examples**: Relate your explanations to concrete projects or experiences to keep your responses engaging and relevant.\n- **Practice Active Listening**: Rephrase or confirm the question before answering to stay aligned with the interviewer.",
                "Knowledge Accuracy": "- **Deepen Technical Knowledge**: Refresh core concepts and be ready to explain them accurately.\n- **Stay Updated**: Keep up with recent developments so your answers reflect current best practices.",
                "Clarity": "- **Use Structured Responses**: Organise answers with clear frameworks such as STAR.\n- **Summarise Key Points**: Close with a brief recap to reinforce your main message."
            }


class RecruiterAgent:
    """Orchestrates the interview flow."""
    
    @staticmethod
    def get_next_question(session) -> str:
        """Get the next question for the session."""
        if session.current_question_index < len(session.questions):
            return session.questions[session.current_question_index]
        return None
    
    @staticmethod
    def get_closing_message(name: str, interview_type: str, overall_scores: Dict) -> str:
        """Generate a personalized closing message based on interview type and performance."""
        if interview_type.lower() == "behavioral":
            # Get average score for a friendly summary
            avg_score = 0
            if overall_scores:
                scores = []
                for metric, score_str in overall_scores.items():
                    try:
                        score = float(score_str.split(':')[1].split('/')[0].strip())
                        scores.append(score)
                    except:
                        pass
                if scores:
                    avg_score = sum(scores) / len(scores)
            
            prompt = f"""Generate a warm, professional closing message for a behavioral mock interview.

Candidate Name: {name}
Average Performance Score: {avg_score:.1f}/10

Requirements:
- Thank the candidate by name
- Provide a brief, encouraging summary of their performance
- Mention specific strengths observed (e.g., communication, thoughtful examples)
- Give one constructive tip for improvement (e.g., structuring answers with clear results)
- Keep it conversational and human-like (not robotic)
- Maximum 2-3 sentences
- Be warm, professional, and encouraging

Example format: "Thank you, [Name]. You showed strong communication and thoughtful examples. Keep structuring your answers with clear results to make them even stronger."

Generate the closing message:"""
            
            try:
                from langchain_openai import ChatOpenAI
                from langchain.schema import HumanMessage
                
                chat = ChatOpenAI(model=MODEL_NAME, temperature=0.8, api_key=OPENAI_API_KEY, max_tokens=MAX_TOKENS)
                response = chat.invoke([HumanMessage(content=prompt)])
                closing_msg = response.content.strip()
                
                # Clean up if it has quotes or extra formatting
                closing_msg = closing_msg.strip('"').strip("'").strip()
                return closing_msg if closing_msg else f"Thank you, {name}. You showed strong communication and thoughtful examples. Keep structuring your answers with clear results to make them even stronger."
            except:
                return f"Thank you, {name}. You showed strong communication and thoughtful examples. Keep structuring your answers with clear results to make them even stronger."
        else:
            return f"Thank you, {name}, for completing the interview. Your detailed feedback is ready."
    
    @staticmethod
    def get_welcome_message(name: str, interview_type: str) -> str:
        """Generate a personalized welcome message based on interview type."""
        if interview_type.lower() == "behavioral":
            prompt = f"""Generate a warm, professional welcome message for a behavioral mock interview.

Candidate Name: {name}

Requirements:
- Start with a friendly greeting using the candidate's name
- Welcome them to their behavioral mock interview
- Briefly explain that you'll ask questions to understand how they handle real-life situations at work
- Keep it conversational and human-like (not robotic)
- Maximum 2-3 sentences
- Be warm, professional, and encouraging

Example format: "Hi [Name], welcome to your behavioral mock interview. I'll ask a few questions to understand how you handle real-life situations at work."

Generate the welcome message:"""
            
            try:
                from langchain_openai import ChatOpenAI
                from langchain.schema import HumanMessage
                
                chat = ChatOpenAI(model=MODEL_NAME, temperature=0.8, api_key=OPENAI_API_KEY, max_tokens=MAX_TOKENS)
                response = chat.invoke([HumanMessage(content=prompt)])
                welcome_msg = response.content.strip()
                
                # Clean up if it has quotes or extra formatting
                welcome_msg = welcome_msg.strip('"').strip("'").strip()
                return welcome_msg if welcome_msg else f"Hi {name}, welcome to your behavioral mock interview. I'll ask a few questions to understand how you handle real-life situations at work."
            except:
                return f"Hi {name}, welcome to your behavioral mock interview. I'll ask a few questions to understand how you handle real-life situations at work."
        else:
            return None  # No welcome message for non-behavioral interviews
    
    @staticmethod
    def get_polite_message(message_type: str) -> str:
        """Get polite, conversational messages."""
        messages = {
            "repeat": "Of course! Let me repeat that question for you.",
            "pause": "Take your time. I'm here whenever you're ready to continue.",
            "welcome": "Welcome! I'm excited to learn more about your background.",
            "next": [
                "Great! Let's move on to the next question.",
                "Excellent! Here's the next question for you.",
                "Thank you for that answer. Let's continue with the next question.",
                "Well done! Moving forward to the next question.",
                "I appreciate your response. Let's proceed to the next question.",
                "Good answer! Here's what I'd like to ask next.",
                "Thanks for sharing that. Let's explore the next question.",
                "That's helpful. Moving on to the next question now."
            ],
            "complete": "Thank you for completing the interview! I'll prepare your detailed feedback now."
        }
        
        if message_type == "next":
            return random.choice(messages["next"])
        



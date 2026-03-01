#!/usr/bin/env python3
"""
Script to extract questions and answers from PDF files and store them in the database.
Usage: python process_pdf_questions.py <pdf_path> <interview_type> <skill>
Example: python process_pdf_questions.py pdfs/technical_machinelearning.pdf technical MachineLearning
"""

import os
import sys
import re
import json
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from db_handler import insert_qna_rows

# Load environment variables
load_dotenv()

def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file"""
    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        print(f"[INFO] Extracting text from: {pdf_path}")
        reader = PdfReader(pdf_path)
        text = ""
        
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            text += f"\n--- Page {page_num} ---\n{page_text}\n"
            print(f"  [OK] Extracted page {page_num} ({len(page_text)} characters)")
        
        print(f"[SUCCESS] Total text extracted: {len(text)} characters")
        return text
    
    except Exception as e:
        print(f"[ERROR] Error extracting text from PDF: {e}")
        raise

def parse_qa_from_text(text):
    """
    Parse questions and answers from extracted text.
    Pattern: "1: Question text? Answer: Explanation text" followed by "2:" or end
    - Number (e.g., "1:") indicates start of question
    - Question text goes until question mark "?"
    - "Answer:" indicates start of explanation (word "Answer:" is NOT included in explanation)
    - Explanation continues until next number (e.g., "2:") or end
    """
    qa_pairs = []
    
    # Primary pattern: Number followed by question (until ?), then Answer: followed by explanation (until next number)
    # Pattern matches: "1: Question text? Answer: Explanation text" followed by "2:" or end
    # Use non-greedy match for question, but greedy match for explanation to capture full text
    pattern = re.compile(
        r'(\d+)[:\.\)]\s*(.+?\?)\s*Answer:\s*(.+?)(?=\s*\d+[:\.\)]\s*|$)',
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    
    matches = pattern.findall(text)
    
    if matches:
        print(f"[INFO] Found {len(matches)} Q&A pairs using numbered pattern (N: Question? Answer: Explanation)")
        for match in matches:
            if len(match) >= 3:
                question_num = match[0]
                question_text = clean_text(match[1])
                answer_text = clean_text(match[2])
                
                # Remove any "Answer:" that might be in the question text
                if 'Answer:' in question_text:
                    parts = question_text.split('Answer:', 1)
                    question_text = parts[0].strip()
                    # If answer was in question, prepend it to answer_text
                    if len(parts) > 1 and parts[1].strip():
                        answer_text = parts[1].strip() + ' ' + answer_text
                
                # Ensure question ends with ?
                if not question_text.endswith('?'):
                    # Try to find the question mark in the text
                    q_mark_pos = question_text.rfind('?')
                    if q_mark_pos > 0:
                        question_text = question_text[:q_mark_pos + 1]
                
                # Clean answer - remove any trailing number patterns that might have been captured
                answer_text = re.sub(r'\s+\d+[:\.\)].*$', '', answer_text, flags=re.MULTILINE)
                answer_text = clean_text(answer_text)
                
                # Remove number prefix if it's still in question (shouldn't be, but just in case)
                question_text = re.sub(r'^\d+[:\.\)]\s*', '', question_text).strip()
                
                if question_text and answer_text and len(question_text) > 5 and '?' in question_text:
                    qa_pairs.append({
                        'question': question_text,
                        'answer': answer_text
                    })
    
    # If primary pattern didn't work, try unnumbered pattern (no numbers, just Question? Answer:)
    if len(qa_pairs) < 3:
        print("[INFO] Trying unnumbered pattern (Question? Answer: Explanation)...")
        # Pattern: Questions start with specific question words, end with ?, followed by Answer:
        question_words = r'(?:Why|What|How|When|Where|Explain|Describe|Define|Which|Who|Can|Will|Should|Would|Does|Do|Is|Are|Was|Were|Have|Has|Had|Could|Might|May|Must|Shall)'
        
        # Find all question patterns: question word + text until ? + Answer:
        pattern = re.compile(
            r'(?:^|\n)\s*(' + question_words + r'[^?]*\?)\s*Answer:\s*(.+?)(?=\n\s*' + question_words + r'[^?]*\?\s*Answer:|$)',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        
        matches = pattern.findall(text)
        if matches:
            print(f"[INFO] Found {len(matches)} Q&A pairs using unnumbered pattern")
            for match in matches:
                if len(match) >= 2:
                    question_text = clean_text(match[0])
                    answer_text = clean_text(match[1])
                    
                    # Remove page markers
                    question_text = re.sub(r'---\s*Page\s*\d+\s*---', '', question_text, flags=re.IGNORECASE)
                    answer_text = re.sub(r'---\s*Page\s*\d+\s*---', '', answer_text, flags=re.IGNORECASE)
                    
                    # Clean answer - remove any trailing question patterns
                    answer_text = re.sub(r'\s+' + question_words + r'[^?]*\?\s*Answer:.*$', '', answer_text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    
                    question_text = clean_text(question_text)
                    answer_text = clean_text(answer_text)
                    
                    if question_text and answer_text and len(question_text) > 5 and '?' in question_text:
                        qa_pairs.append({
                            'question': question_text,
                            'answer': answer_text
                        })
    
    # If still not enough, try alternative patterns
    if len(qa_pairs) < 3:
        print("[INFO] Trying alternative parsing patterns...")
        
        # Alternative 1: Look for "Answer:" after question marks with numbers
        alt_pattern1 = re.compile(
            r'(\d+)[:\.\)]\s*(.+?\?)\s*(?:Answer|Solution)[:\-\.]?\s*(.+?)(?=\s*\d+[:\.\)]|$)',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        
        matches = alt_pattern1.findall(text)
        if matches:
            print(f"[INFO] Found {len(matches)} Q&A pairs using alternative pattern 1")
            for match in matches:
                if len(match) >= 3:
                    question_text = clean_text(match[1])
                    answer_text = clean_text(match[2])
                    # Remove number prefix
                    question_text = re.sub(r'^\d+[:\.\)]\s*', '', question_text).strip()
                    if question_text and answer_text and len(question_text) > 5:
                        qa_pairs.append({
                            'question': question_text,
                            'answer': answer_text
                        })
    
    # If still not enough, use fallback
    if len(qa_pairs) < 3:
        print("[WARNING] Using fallback parsing strategy...")
        qa_pairs = fallback_parse(text)
    
    return qa_pairs

def clean_text(text):
    """Clean and normalize extracted text"""
    if not text:
        return ""
    
    # Remove page markers like "--- Page 2 ---"
    text = re.sub(r'---\s*Page\s*\d+\s*---', '', text, flags=re.IGNORECASE)
    # Remove common PDF artifacts
    text = re.sub(r'\f', '', text)  # Form feed
    text = re.sub(r'\x0c', '', text)  # Form feed
    # Remove extra whitespace but preserve single spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    # Remove standalone page numbers
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    
    return text

def fallback_parse(text):
    """
    Fallback parsing strategy: Process line by line to identify numbered Q&A pairs
    Pattern: "N: Question? Answer: Explanation"
    """
    qa_pairs = []
    
    # Split text into lines for processing
    lines = text.split('\n')
    
    current_question = None
    current_answer_parts = []
    in_answer = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if line starts with a number (new question)
        number_match = re.match(r'^(\d+)[:\.\)]\s*(.+)$', line)
        if number_match:
            # Save previous Q&A pair if exists
            if current_question and current_answer_parts:
                answer_text = ' '.join(current_answer_parts).strip()
                if answer_text:
                    qa_pairs.append({
                        'question': current_question,
                        'answer': answer_text
                    })
            
            # Start new question
            question_text = number_match.group(2)
            # Remove number prefix if present
            question_text = re.sub(r'^\d+[:\.\)]\s*', '', question_text).strip()
            # Check if question ends with ? and has Answer:
            if '?' in question_text and 'Answer:' in question_text:
                parts = question_text.split('Answer:', 1)
                current_question = parts[0].strip()
                if not current_question.endswith('?'):
                    q_pos = current_question.rfind('?')
                    if q_pos > 0:
                        current_question = current_question[:q_pos + 1]
                current_answer_parts = [parts[1].strip()] if parts[1].strip() else []
                in_answer = True
            elif '?' in question_text:
                # Extract just the question part (up to ?)
                q_pos = question_text.rfind('?')
                if q_pos > 0:
                    current_question = question_text[:q_pos + 1].strip()
                else:
                    current_question = question_text
                current_answer_parts = []
                in_answer = False
            else:
                current_question = question_text
                current_answer_parts = []
                in_answer = False
        elif current_question:
            # Check if line starts with "Answer:"
            if re.match(r'^Answer:\s*(.+)$', line, re.IGNORECASE):
                answer_match = re.match(r'^Answer:\s*(.+)$', line, re.IGNORECASE)
                current_answer_parts = [answer_match.group(1).strip()]
                in_answer = True
            elif in_answer:
                # Continue collecting answer until next number
                # Check if this line starts with a number (next question)
                if re.match(r'^\d+[:\.\)]', line):
                    # This is the next question, save current pair
                    answer_text = ' '.join(current_answer_parts).strip()
                    if answer_text:
                        qa_pairs.append({
                            'question': current_question,
                            'answer': answer_text
                        })
                    # Start new question
                    number_match = re.match(r'^(\d+)[:\.\)]\s*(.+)$', line)
                    if number_match:
                        question_text = number_match.group(2)
                        question_text = re.sub(r'^\d+[:\.\)]\s*', '', question_text).strip()
                        if '?' in question_text:
                            q_pos = question_text.rfind('?')
                            if q_pos > 0:
                                current_question = question_text[:q_pos + 1].strip()
                            else:
                                current_question = question_text
                        else:
                            current_question = question_text
                        current_answer_parts = []
                        in_answer = False
                else:
                    # Continue collecting answer
                    current_answer_parts.append(line)
            elif '?' in line:
                # Might be continuation of question
                current_question += ' ' + line
    
    # Don't forget the last pair
    if current_question and current_answer_parts:
        answer_text = ' '.join(current_answer_parts).strip()
        if answer_text:
            qa_pairs.append({
                'question': current_question,
                'answer': answer_text
            })
    
    return qa_pairs

def save_to_json(qa_pairs, output_path):
    """Save Q&A pairs to JSON file"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(qa_pairs, f, indent=2, ensure_ascii=False)
        print(f"[SUCCESS] Saved {len(qa_pairs)} Q&A pairs to: {output_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Error saving to JSON: {e}")
        return False

def store_in_database(qa_pairs, table_name):
    """Store Q&A pairs in the database"""
    if not qa_pairs:
        print("[WARNING] No Q&A pairs to store")
        return False
    
    try:
        print(f"[INFO] Storing {len(qa_pairs)} Q&A pairs in database table: {table_name}")
        
        # Prepare data for insertion
        qna_rows = []
        for qa in qa_pairs:
            question = qa.get('question', '').strip()
            answer = qa.get('answer', '').strip()
            
            if question and answer:
                qna_rows.append((question, answer))
        
        if not qna_rows:
            print("[WARNING] No valid Q&A pairs to insert")
            return False
        
        # Insert into database using the existing function
        insert_qna_rows(table_name, qna_rows)
        print(f"[SUCCESS] Successfully stored {len(qna_rows)} Q&A pairs in table '{table_name}'")
        return True
    
    except Exception as e:
        print(f"[ERROR] Error storing in database: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_table_name(interview_type, skill):
    """Get database table name based on interview type and skill"""
    normalized_type = interview_type.lower() if interview_type else 'default'
    
    if normalized_type == 'behavioral':
        return 'behavioralquestions'
    
    # Convert skill to lowercase and replace spaces
    skill_normalized = skill.lower().replace(' ', '')
    return f"{interview_type}_{skill_normalized}"

def main():
    if len(sys.argv) < 4:
        print("Usage: python process_pdf_questions.py <pdf_path> <interview_type> <skill>")
        print("Example: python process_pdf_questions.py pdfs/technical_machinelearning.pdf technical MachineLearning")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    interview_type = sys.argv[2]
    skill = sys.argv[3]
    
    print("=" * 60)
    print("PDF Question Extraction and Database Storage")
    print("=" * 60)
    print(f"PDF Path: {pdf_path}")
    print(f"Interview Type: {interview_type}")
    print(f"Skill: {skill}")
    print("=" * 60)
    print()
    
    # Step 1: Extract text from PDF
    try:
        text = extract_text_from_pdf(pdf_path)
    except Exception as e:
        print(f"[ERROR] Failed to extract text: {e}")
        sys.exit(1)
    
    # Step 2: Parse Q&A pairs from text
    print("\n[INFO] Parsing questions and answers from extracted text...")
    qa_pairs = parse_qa_from_text(text)
    
    if not qa_pairs:
        print("[ERROR] No Q&A pairs found in the PDF. Please check the PDF format.")
        print("\nTip: The PDF should contain questions and answers in formats like:")
        print("   - Q: Question text\n   A: Answer text")
        print("   - 1. Question text\n   Answer: Answer text")
        print("   - Question text?\n   Answer text")
        sys.exit(1)
    
    print(f"[SUCCESS] Found {len(qa_pairs)} Q&A pairs")
    
    # Step 3: Save to JSON (optional backup)
    json_path = pdf_path.replace('.pdf', '_qa.json')
    if os.path.dirname(json_path) == 'pdfs':
        json_path = os.path.join(os.path.dirname(os.path.dirname(pdf_path)), os.path.basename(json_path))
    save_to_json(qa_pairs, json_path)
    
    # Step 4: Store in database
    table_name = get_table_name(interview_type, skill)
    print(f"\n[INFO] Storing in database table: {table_name}")
    
    success = store_in_database(qa_pairs, table_name)
    
    if success:
        print("\n" + "=" * 60)
        print("[SUCCESS] PROCESS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Summary:")
        print(f"   - Q&A pairs extracted: {len(qa_pairs)}")
        print(f"   - JSON backup saved: {json_path}")
        print(f"   - Database table: {table_name}")
        print(f"\nYou can now verify the data:")
        print(f"   - Check JSON file: {json_path}")
        print(f"   - Query database table: {table_name}")
        print(f"   - API endpoint: /api/questions/{interview_type}/{skill}")
    else:
        print("\n" + "=" * 60)
        print("[ERROR] PROCESS COMPLETED WITH ERRORS")
        print("=" * 60)
        sys.exit(1)

if __name__ == '__main__':
    main()


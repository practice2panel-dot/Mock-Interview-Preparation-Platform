import os
from functools import lru_cache
from typing import Optional, Tuple
from docx import Document

RUBRICS_DOCX = os.path.join(os.path.dirname(__file__), "Rubrics", "Rubrics.docx")

@lru_cache(maxsize=1)
def extract_rubrics_docx() -> Optional[str]:
    """
    Extract all rubric content from the Rubrics.docx file.
    This extracts the entire document content (relaxed rubrics version).
    """
    if not os.path.isfile(RUBRICS_DOCX):
        return None
    
    try:
        doc = Document(RUBRICS_DOCX)
        # Extract all paragraphs, filtering out empty ones
        para_texts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        if not para_texts:
            return None

        # Join all paragraphs with newlines to preserve structure
        rubric_text = "\n".join(para_texts)
        return rubric_text
    except Exception as e:
        print(f"Error extracting rubrics from docx: {e}")
        return None

@lru_cache(maxsize=8)
def load_rubric_text(skill: str = "", interview_type: str = "") -> Tuple[Optional[str], Optional[str]]:
    """
    Load rubric text from Rubrics.docx file for all interview types.
    The new relaxed rubrics are used for all interview types including behavioral.
    
    Args:
        skill: Skill name (not used, kept for compatibility)
        interview_type: Type of interview ('behavioral', 'technical', etc.)
    
    Returns:
        Tuple of (rubric_text, rubric_source)
    """
    # Use the relaxed rubrics from docx for all interview types
    rubric_text = extract_rubrics_docx()
    if rubric_text:
        return rubric_text, "Rubrics.docx (Relaxed Version)"
    return None, None

if __name__ == "__main__":
    print("[Rubric Extraction Debug]")
    text = extract_rubrics_docx()
    if not text:
        print("No rubric content extracted from Rubrics.docx!")
    else:
        print("Rubric extraction result:\n---------------------")
        print(f"Total length: {len(text)} characters")
        print(f"Number of lines: {len(text.split(chr(10)))}")
        print("\nFull content:\n---")
        print(text)
        print("---- \nEnd of rubric extraction output\n---")



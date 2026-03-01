import os
from docx import Document

path = os.path.join(os.path.dirname(__file__), "Rubrics", "Rubrics.docx")
doc = Document(path)
for i, para in enumerate(doc.paragraphs):
    txt = para.text.strip()
    if txt:
        print(f"{i}: {txt}")

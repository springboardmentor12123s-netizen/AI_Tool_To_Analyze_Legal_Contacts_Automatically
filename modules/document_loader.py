from pypdf import PdfReader
from docx import Document
import tempfile

def load_document(uploaded_file):
    suffix = uploaded_file.name.split(".")[-1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    if suffix == "pdf":
        reader = PdfReader(tmp_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text

    elif suffix == "docx":
        doc = Document(tmp_path)
        return "\n".join([p.text for p in doc.paragraphs])

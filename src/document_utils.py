from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import PyPDF2


def extract_text_from_pdf(file_path: str) -> str:
    """Extracts raw text from a PDF file."""
    text = ""
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def create_documents_from_text(text: str, source_name: str) -> list[Document]:
    """Splits text into chunks and wraps them in Document objects."""
    # We use overlapping chunks so clauses don't get cut in half
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_text(text)
    
    return [
        Document(
            page_content=chunk, 
            metadata={"source": source_name, "chunk_index": i}
        ) 
        for i, chunk in enumerate(chunks)
    ]
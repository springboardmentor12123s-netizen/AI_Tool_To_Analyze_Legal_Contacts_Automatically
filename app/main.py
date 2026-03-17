import os

from app.utils.document_loader import load_document
from app.utils.text_processing import chunk_text

from app.services.vector_store import store_chunks
from app.services.report_service import pretty_print

from app.workflow.contract_graph import build_graph


NAMESPACE = "contracts"


def main():

    file_path = input("Enter the PDF, DOCX, or TXT file path: ")

    document_text = load_document(file_path)

    # Ensure the document text is a single string
    if isinstance(document_text, list):
        document_text = "\n".join(document_text)

    chunks = chunk_text(document_text)

    print(f"\nTotal Chunks Created: {len(chunks)}")

    store_chunks(chunks, namespace=NAMESPACE)

    print("\nChunks stored in Pinecone successfully.")

    graph = build_graph()

    result = graph.invoke({})

    #print("\n========= FINAL ANALYSIS =========\n")

    pretty_print(result)


if __name__ == "__main__":
    main()
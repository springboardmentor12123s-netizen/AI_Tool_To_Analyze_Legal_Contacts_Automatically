import re
import nltk
from nltk.tokenize import sent_tokenize


def clean_text(text: str) -> str:
    """
    Cleans extra whitespace and formatting noise.
    """
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def split_into_sentences(text: str):
    """
    Splits text into sentences using NLTK.
    """
    return sent_tokenize(text)


def chunk_sentences(sentences, max_words=800):
    """
    Groups sentences into chunks of approximately max_words.
    """

    chunks = []
    current_chunk = []
    current_word_count = 0

    for sentence in sentences:

        word_count = len(sentence.split())

        if current_word_count + word_count > max_words:

            chunks.append(" ".join(current_chunk))

            current_chunk = []
            current_word_count = 0

        current_chunk.append(sentence)

        current_word_count += word_count

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def process_text_pipeline(raw_text: str):
    """
    Full pipeline:
    Clean → Sentence Split → Chunk
    """

    cleaned = clean_text(raw_text)

    sentences = split_into_sentences(cleaned)

    chunks = chunk_sentences(sentences)

    return chunks



def chunk_text(text: str):
    """
    Wrapper function used by main.py
    """
    return process_text_pipeline(text)
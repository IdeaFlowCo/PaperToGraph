"""
Utilities for interacting with input text.
"""

import tiktoken


from utils import log_msg


TEXT_BLOCK_SIZE_LIMIT = 6000


def is_text_oversized(text):
    return len(text) > TEXT_BLOCK_SIZE_LIMIT


def normalize_line_endings(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_to_size(text: str, limit=TEXT_BLOCK_SIZE_LIMIT):
    text = normalize_line_endings(text)

    # Split by paragraphs first
    paragraph_chunks = list(filter(lambda x: x != "", text.split("\n\n")))

    # Any paragraph that is too long, split by sentences
    text_chunks = []
    for chunk in paragraph_chunks:
        if len(chunk) > limit:
            # Split by sentences
            sentences = chunk.split(". ")
            new_chunk = ""
            for sentence in sentences:
                if len(new_chunk) + len(sentence) < limit:
                    new_chunk += sentence + ". "
                else:
                    text_chunks.append(new_chunk)
                    new_chunk = sentence + ". "
            text_chunks.append(new_chunk)
        else:
            text_chunks.append(chunk)

    # Try to recombine chunks that are smaller than they need to be
    rechunked_text = [text_chunks[0]]
    i = 0
    j = 1
    while j < len(text_chunks):
        if len(rechunked_text[i]) + len(text_chunks[j]) < limit:
            rechunked_text[i] = rechunked_text[i] + "\n\n" + text_chunks[j]
            j += 1
        else:
            i += 1
            rechunked_text.append(text_chunks[j])
            j += 1

    log_msg(f"Split into {len(rechunked_text)} blocks of text")

    return rechunked_text


def get_token_length(text, model="gpt-3.5-turbo"):
    """
    Returns the number of tokens in the given text for the specified model.
    """
    # Map new model names to their base tokenizer
    if model.startswith("gpt-4o"):
        encoding = tiktoken.get_encoding(
            "cl100k_base"
        )  # GPT-4 and ChatGPT use cl100k_base
    else:
        encoding = tiktoken.encoding_for_model(model)
    text_as_tokens = encoding.encode(text)
    return len(text_as_tokens)


def __split_paragraph_to_token_size(
    paragraph: str, token_limit: int, model="gpt-3.5-turbo"
):
    encoding = tiktoken.encoding_for_model(model)
    text_as_tokens = encoding.encode(paragraph)
    text_chunks = []
    # Make each chunk 10 tokens smaller than the limit, to leave some room for error
    chunk_size = token_limit - 10
    while len(text_as_tokens) > token_limit:
        token_chunk = text_as_tokens[:chunk_size]
        text_chunks.append(encoding.decode(token_chunk))
        text_as_tokens = text_as_tokens[chunk_size:]
    text_chunks.append(encoding.decode(text_as_tokens))
    return text_chunks


def split_to_token_size(text: str, token_limit: int, model="gpt-3.5-turbo"):
    text = normalize_line_endings(text)

    # Convenience function to make sure we're always passing model argument to get_token_length
    def token_length(t):
        return get_token_length(t, model=model)

    # Split by paragraphs first
    paragraph_chunks = list(filter(lambda x: x != "", text.split("\n\n")))

    text_chunks = []
    for chunk in paragraph_chunks:
        if token_length(chunk) < token_limit:
            # If paragraph is small enough, just add it to the list
            # Add back the double newline that was removed by the split for use in rechunking logic below
            text_chunks.append(chunk + "\n\n")
        else:
            # Further split any paragraph that is too long into chunks using token boundaries
            chunks_for_paragraph = __split_paragraph_to_token_size(
                chunk, token_limit, model=model
            )
            text_chunks.extend(chunks_for_paragraph)

    # Try to recombine chunks that are smaller than they need to be
    rechunked_text = [text_chunks[0]]
    i = 0
    j = 1
    while j < len(text_chunks):
        if not rechunked_text[i].endswith("\n\n"):
            # Don't try to recombine any chunk that wasn't its own paragraph
            rechunked_text.append(text_chunks[j])
            i += 1
            j += 1
            continue
        if token_length(rechunked_text[i]) + token_length(text_chunks[j]) < token_limit:
            rechunked_text[i] = rechunked_text[i] + text_chunks[j]
            j += 1
        else:
            rechunked_text.append(text_chunks[j])
            i += 1
            j += 1

    log_msg(f"Split into {len(rechunked_text)} blocks of text")

    return rechunked_text

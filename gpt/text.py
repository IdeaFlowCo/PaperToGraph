'''
Utilities for interacting with input text.
'''

import tiktoken


from utils import log_msg


TEXT_BLOCK_SIZE_LIMIT = 6000


def is_text_oversized(text):
    return len(text) > TEXT_BLOCK_SIZE_LIMIT


def normalize_line_endings(text):
    return text.replace('\r\n', '\n').replace('\r', '\n')


def split_to_size(text: str, limit=TEXT_BLOCK_SIZE_LIMIT):
    text = normalize_line_endings(text)

    # Split by paragraphs first
    paragraph_chunks = list(filter(lambda x: x != '', text.split('\n\n')))

    # Any paragraph that is too long, split by sentences
    text_chunks = []
    for chunk in paragraph_chunks:
        if len(chunk) > limit:
            # Split by sentences
            sentences = chunk.split('. ')
            new_chunk = ''
            for sentence in sentences:
                if len(new_chunk) + len(sentence) < limit:
                    new_chunk += sentence + '. '
                else:
                    text_chunks.append(new_chunk)
                    new_chunk = sentence + '. '
            text_chunks.append(new_chunk)
        else:
            text_chunks.append(chunk)

    # Try to recombine chunks that are smaller than they need to be
    rechunked_text = [text_chunks[0]]
    i = 0
    j = 1
    while j < len(text_chunks):
        if len(rechunked_text[i]) + len(text_chunks[j]) < limit:
            rechunked_text[i] = rechunked_text[i] + '\n\n' + text_chunks[j]
            j += 1
        else:
            i += 1
            rechunked_text.append(text_chunks[j])
            j += 1

    log_msg(f'Split into {len(rechunked_text)} blocks of text')

    return rechunked_text


def get_token_length(text, model='gpt-3.5-turbo'):
    encoding = tiktoken.encoding_for_model(model)
    text_as_tokens = encoding.encode(text)
    return len(text_as_tokens)


def split_to_token_size(text: str, token_limit: int, model='gpt-3.5-turbo'):
    text = normalize_line_endings(text)

    # Convenience function to make sure we're always passing model argument to get_token_length
    def token_length(t): return get_token_length(t, model=model)

    # Split by paragraphs first
    paragraph_chunks = list(filter(lambda x: x != '', text.split('\n\n')))

    # Any paragraph that is too long, split by sentences
    text_chunks = []
    for chunk in paragraph_chunks:
        if token_length(chunk) > token_limit:
            # Split by sentences
            sentences = chunk.split('. ')
            new_chunk = ''
            for sentence in sentences:
                if token_length(new_chunk) + token_length(sentence) < token_limit:
                    new_chunk += sentence + '. '
                else:
                    text_chunks.append(new_chunk)
                    new_chunk = sentence + '. '
            text_chunks.append(new_chunk)
        else:
            text_chunks.append(chunk)

    # Try to recombine chunks that are smaller than they need to be
    rechunked_text = [text_chunks[0]]
    i = 0
    j = 1
    while j < len(text_chunks):
        if token_length(rechunked_text[i]) + token_length(text_chunks[j]) < token_limit:
            rechunked_text[i] = rechunked_text[i] + '\n\n' + text_chunks[j]
            j += 1
        else:
            i += 1
            rechunked_text.append(text_chunks[j])
            j += 1

    log_msg(f'Split into {len(rechunked_text)} blocks of text')

    return rechunked_text

'''
Utilities for interacting with input text.
'''

from utils import log_msg



TEXT_BLOCK_SIZE_LIMIT = 6000


def is_text_oversized(text):
    return len(text) > TEXT_BLOCK_SIZE_LIMIT


def split_to_size(text:str, limit=TEXT_BLOCK_SIZE_LIMIT):
    # Split by paragraphs first
    og_text_chunks = list(filter(lambda x : x != '', text.split('\n\n')))

    # Try to recombine chunks that are smaller than they need to be
    rechunked_text = [og_text_chunks[0]]
    i = 0
    j = 1
    while j < len(og_text_chunks):
        if len(rechunked_text[i]) + len(og_text_chunks[j]) < limit:
            rechunked_text[i] = rechunked_text[i] + '\n\n' + og_text_chunks[j]
            j += 1
        else:
            i += 1
            rechunked_text.append(og_text_chunks[j])
            j += 1

    log_msg(f'Split into {len(rechunked_text)} blocks of text')

    return rechunked_text


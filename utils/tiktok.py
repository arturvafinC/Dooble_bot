import tiktoken
encoding = tiktoken.get_encoding('cl100k_base')


def count_tokens(text):
    if text:
        transcription_tokens = len(encoding.encode(text)) + 4
        return transcription_tokens
    return 0

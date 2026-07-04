import tiktoken

encoding = None


def count_tokens(text):
    global encoding

    if text:
        if encoding is None:
            encoding = tiktoken.get_encoding('cl100k_base')
        transcription_tokens = len(encoding.encode(text)) + 4
        return transcription_tokens
    return 0

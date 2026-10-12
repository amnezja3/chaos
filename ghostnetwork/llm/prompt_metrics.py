"""Local size diagnostics, not a tokenizer or a provider billing estimate."""
import hashlib
import json


def prompt_metrics(package):
    messages = package['messages']
    schema = package['format']
    contents = [message['content'] for message in messages]
    encode = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':')).encode('utf-8')
    return {
        'message_chars': sum(len(content) for content in contents),
        'message_bytes': sum(len(content.encode('utf-8')) for content in contents),
        'schema_bytes': len(encode(schema)),
        'prompt_sha256': hashlib.sha256(encode({'messages': messages, 'schema': schema})).hexdigest(),
    }

"""Redact callback query strings in Python access logs (proxy configured separately)."""
import logging
import re


class CallbackQueryFilter(logging.Filter):
    def filter(self, record):
        message=record.getMessage()
        if '/auth/' in message:
            record.msg=re.sub(r'(/auth/[^\s?"\']+)\?[^\s"\']+',r'\1?<redacted>',message)
            record.args=()
        return True


def install():
    for name in ('werkzeug','gunicorn.access'):
        logger=logging.getLogger(name)
        if not any(isinstance(item,CallbackQueryFilter) for item in logger.filters):
            logger.addFilter(CallbackQueryFilter())

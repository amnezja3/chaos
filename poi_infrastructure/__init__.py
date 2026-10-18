"""Shared raw OSM infrastructure; no player state belongs here."""
import logging


def logger():
    log = logging.getLogger('chaos.poi')
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
    return log

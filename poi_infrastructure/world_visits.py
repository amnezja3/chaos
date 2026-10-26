"""Anonymous sector demand from committed positions. No schema creation or HTTP."""
import logging
import os
from pathlib import Path

from .discovery_queue import DemandQueue
from .repository import Repository


def record_visit(position):
    if (os.environ.get('CHAOS_POI_WORLD_VISITS_ENABLED') != '1'
            or os.environ.get('CHAOS_POI_DISCOVERY_MODE') != 'passive'):
        return 0
    try:
        path = Path(os.environ.get('CHAOS_POI_CACHE_PATH','data/poi_cache.sqlite3'))
        if not path.is_file(): return 0
        # No username, route, session or exact point is persisted by DemandQueue.
        return DemandQueue(Repository(path)).record(position['lng'],position['lat'],min_interval=60)
    except Exception as exc:
        logging.getLogger(__name__).debug('world_visit skipped error_type=%s',type(exc).__name__)
        return 0

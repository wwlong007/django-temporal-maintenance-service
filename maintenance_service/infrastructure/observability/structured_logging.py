import logging

logger = logging.getLogger("maintenance_service")


def event(name, **fields):
    logger.info("calendar_event", extra={"event_name": name, **fields})

import logging
import os
from logging.config import dictConfig

def logger_setup():
    if not os.path.isdir("logs"):
        os.mkdir("logs")
    with open("logs/info.log", "a") as f:
        pass
    logger = logging.getLogger("bot")
    return logger


LOGGING_CONFIG = {
    "version": 1,
    "disabled_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(levelname)-8s - %(module)-16s : %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "discord": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "logs/info.log",
            "mode": "a",
            "formatter": "standard",
        },
    },
    "loggers": {
        "bot": {
            "handlers": ["console", "file"], 
            "level": "INFO", 
            "propagate": False
        },
        "discord": {
            "handlers": ["discord", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

dictConfig(LOGGING_CONFIG)
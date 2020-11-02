import os
import logging
import logging.config


LOG_SETTINGS = {
    'version': 1,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s %(levelname)s %(process)d %(name)s.%(lineno)d %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': '/var/log/cdsstack/baremetal-api.log',
            'mode': 'a',
            'maxBytes': 10485760,
            'backupCount': 5,
        },

    },
    'loggers': {
        '': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False
        },
    }
}


def setup(path='/var/log/bmstools'):
    if not os.path.exists(path):
        os.makedirs(path)
    logging.config.dictConfig(LOG_SETTINGS)

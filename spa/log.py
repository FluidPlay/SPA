import logging
import os
import time


class ClockFormatter(logging.Formatter):
    def format(self, record):
        record.clockTime = time.clock()
        return super(ClockFormatter, self).format(record)


def setup_default_logger():
    logger = logging.getLogger('spa')
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.DEBUG)

    filename = os.getenv('SPA_DEBUG_LOG', 'debug.log')

    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    fh = logging.FileHandler(filename)
    fh.setLevel(logging.DEBUG)

    formatter = ClockFormatter(
        fmt='%(asctime)s\t%(threadName)s\t%(clockTime)s\t%(levelname)s\t'
            '%(filename)s:%(lineno)d\t%(funcName)s\t%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

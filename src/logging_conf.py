from loguru import logger
import sys

def setup_logging(): 
    logger.remove()
    logger.add(sys.stdout, level="INFO", enqueue=True, backtrace=False, diagnose=False)
    logger.add("logs/run_{time}.log", level="DEBUG", rotation="5 MB", retention="7 days")
    return logger
    

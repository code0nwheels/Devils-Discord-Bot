"""
Centralized logging setup utility.
Extracts the repeated RotatingFileHandler pattern used across all cogs.
"""
import logging
from logging.handlers import RotatingFileHandler


def setup_logger(name: str, log_file: str) -> logging.Logger:
	"""
	Set up a logger with rotating file handler.
	
	Args:
		name: Logger name (typically __name__)
		log_file: Path to log file (e.g., 'log/admin.log')
	
	Returns:
		Configured logger instance
	"""
	logger = logging.getLogger(name)
	logger.setLevel(logging.INFO)
	
	# Add rotating handler
	handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
	
	# Create logging format
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	
	return logger


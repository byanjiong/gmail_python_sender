import os
import logging

def setup_logging(filename='process.log'):
    """
    Configures the global logging settings.
    Call this at the start of any script to enable logging to 'log/process.log'.
    """
    # 1. Define paths
    # Assumes log.py is in the root project folder
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, 'log')
    log_file = os.path.join(log_dir, filename)

    # 2. Ensure log directory exists
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        print(f"Error creating log directory: {e}")

    # 3. Configure the logging module
    # 'force=True' ensures this configuration overwrites any previous configs
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True 
    )
    
    # Return the logger instance if needed, though logging.* functions will now work globally
    return logging.getLogger()
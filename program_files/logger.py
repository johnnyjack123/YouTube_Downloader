import logging

debug_log_file = "debug.log"

logger = logging.getLogger("debug_logger")
logger.setLevel(logging.INFO)

# Formatierten File Handler
file_handler = logging.FileHandler(debug_log_file)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s -  %(filename)s:%(lineno)d - %(message)s", "%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)

# Roh-Datei Handler ohne Formatierung (nur Nachricht)
raw_file_handler = logging.FileHandler(debug_log_file)
raw_file_handler.setLevel(logging.INFO)
raw_file_handler.setFormatter(logging.Formatter("%(message)s"))

# Standard: formatierten Handler hinzufügen
logger.addHandler(file_handler)

def log_message(message, raw=False):
    if raw:
        # Vorübergehend nur den rohen Handler benutzen
        logger.removeHandler(file_handler)
        logger.addHandler(raw_file_handler)
        logger.info(message)
        logger.removeHandler(raw_file_handler)
        logger.addHandler(file_handler)
    else:
        logger.info(message)
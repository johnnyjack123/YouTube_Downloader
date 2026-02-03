import program_files.globals as global_variables
import json
from program_files.logger import logger

count = 0

def deep_update_with_defaults(entry: dict, defaults: dict) -> dict:
    """Rekursiv Defaults in Entry mergen, ohne bestehende Werte zu überschreiben."""
    global count
    for key, default_value in defaults.items():
        if key not in entry:
            entry[key] = default_value
            count += 1
        elif isinstance(default_value, dict) and isinstance(entry[key], dict):
            deep_update_with_defaults(entry[key], default_value)
    return entry


def update_config_with_defaults(data: dict, defaults: dict) -> dict:
    """
    Aktualisiert JSON-Daten rekursiv:
    - Listen (z. B. userdata, backup_paths) werden über alle Einträge gemerged
    - Dicts (z. B. server_data) werden rekursiv zusammengeführt
    """
    global count
    for key, default_schema in defaults.items():
        if key not in data:
            data[key] = default_schema
            count += 1
        elif isinstance(data[key], list) and isinstance(default_schema, dict):
            for entry in data[key]:
                deep_update_with_defaults(entry, default_schema)
        elif isinstance(data[key], dict) and isinstance(default_schema, dict):
            deep_update_with_defaults(data[key], default_schema)
    return data

def migrate_config():
    global count
    """Lädt Config, migriert sie und speichert sie zurück"""

    # Defaults zusammenstellen
    defaults = {
        "userdata": global_variables.userdata,
        "program_data": global_variables.program_data,
        "download_data": global_variables.download_data
    }

    # JSON laden
    with open(global_variables.userdata_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Schema-Update durchführen (NEUE Funktion!)
    updated_data = update_config_with_defaults(data, defaults)

    # Zurückschreiben
    with open(global_variables.userdata_file, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, indent=4, ensure_ascii=False)

    if count > 0:
        logger.info(f"File successfully merged. {count} entries changed.")
    else:
        logger.info("Nothing merged in userdata file.")
    return updated_data
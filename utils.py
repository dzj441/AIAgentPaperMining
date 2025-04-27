# utils.py

import os
import json
def save_json(file_path: str, datas: list) -> None:
    """Save a list of data to a JSON file."""
    assert isinstance(datas, list), "datas should be a list"
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(datas, f, indent=4, ensure_ascii=False)
# utils.py

import os
import json
import yaml 
def save_json(file_path: str, datas: list) -> None:
    """Save a list of data to a JSON file."""
    assert isinstance(datas, list), "datas should be a list"
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(datas, f, indent=4, ensure_ascii=False)

def load_config(path: str) -> dict:
    """
    load yaml
    """
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

if __name__ == '__main__':
    save_json('result.json', ["https://github.com/aqlaboratory/openfold","https://github.com/jasonkyuyim/multiflow","https://github.com/NVlabs/protcomposer"])
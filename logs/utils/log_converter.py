import json
import os
from collections import Counter

def parse_log_file(log_file_path):
    directory_counter = Counter()
    current_repo = None

    with open(log_file_path, 'r') as log_file:
        for line in log_file:
            line = line.strip()
            if line.startswith("Repository:"):
                current_repo = line.split(":")[1].strip()
            elif current_repo and line:
                directory, count = line.split(":")
                directory = directory.strip()
                count = int(count.strip())
                directory_counter[directory] += count

    return directory_counter

def save_to_json(data, json_file_path):
    with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

if __name__ == "__main__":
    log_file_path = f'{os.getcwd()}\\logs\\log\\common_directories.log'
    print(log_file_path)
    json_file_path = f'{os.getcwd()}\\logs\\json\\common_directories.json'

    directory_counter = parse_log_file(log_file_path)
    save_to_json(directory_counter, json_file_path)

    print(f"Aggregated directory counts saved to {json_file_path}")
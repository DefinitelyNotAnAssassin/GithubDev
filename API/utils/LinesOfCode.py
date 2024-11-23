import os
import shutil
import requests
import io
import zipfile
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tempfile
from collections import Counter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RepoAnalyzer:
    def __init__(self, username, repo_name, ignore_dirs=None, ignore_extensions=None):
        self.username = username
        self.repo_name = repo_name
        self.repo_url_template = "https://github.com/{username}/{repo_name}/archive/refs/heads/{branch}.zip"
        self.ignore_dirs = set(ignore_dirs) if ignore_dirs else set()
        self.ignore_extensions = set(ignore_extensions) if ignore_extensions else set()
        self.clone_base_dir = tempfile.mkdtemp()
        self.clone_dir = self.clone_base_dir  # Will be updated after extraction
        self.directory_counter = Counter()
        logging.info(f"Initialized RepoAnalyzer for {username}/{repo_name}")

    def get_default_branch(self):
        api_url = f"https://api.github.com/repos/{self.username}/{self.repo_name}"
        headers = {}
        token = os.getenv('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = f'token {token}'
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            repo_info = response.json()
            default_branch = repo_info.get('default_branch', 'master')
            logging.info(f"Default branch for {self.username}/{self.repo_name} is {default_branch}")
            return default_branch
        else:
            error_message = f"Failed to get repository info: {response.status_code}"
            logging.error(error_message)
            raise Exception(error_message)

    def download_and_extract_repo(self):
        default_branch = self.get_default_branch()
        repo_url = self.repo_url_template.format(
            username=self.username,
            repo_name=self.repo_name,
            branch=default_branch
        )

        headers = {}
        token = os.getenv('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = f'token {token}'

        logging.info(f"Downloading repository {self.username}/{self.repo_name} from {repo_url}")
        response = requests.get(repo_url, headers=headers, stream=True)
        if response.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(self.clone_base_dir)
            extracted_folder_name = f"{self.repo_name}-{default_branch}"
            self.clone_dir = os.path.join(self.clone_base_dir, extracted_folder_name)
            logging.info(f"Extracted repository to {self.clone_dir}")
        else:
            error_message = f"Failed to download repository: {response.status_code}"
            logging.error(error_message)
            raise Exception(error_message)

    @staticmethod
    def process_file(file_path):
        lines_of_code = 0
        comment_lines = 0
        blank_lines = 0

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    stripped_line = line.strip()
                    if not stripped_line:
                        blank_lines += 1
                    elif stripped_line.startswith(('#', '//', '/*', '*', '*/')):
                        comment_lines += 1
                    else:
                        lines_of_code += 1
            logging.info(f"Processed file {file_path}")
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}")

        return lines_of_code, comment_lines, blank_lines

    def count_lines_of_code(self):
        lines_of_code = 0
        comment_lines = 0
        blank_lines = 0
        lines_of_code_per_language = {}

        files_to_process = []
        for root, dirs, files in os.walk(self.clone_dir):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            for file in files:
                ext = Path(file).suffix
                if ext not in self.ignore_extensions:
                    file_path = os.path.join(root, file)
                    files_to_process.append((file_path, ext))
            # Update directory counter
            self.directory_counter.update(dirs)

        if not files_to_process:
            logging.info("No files to process in the repository.")
            return lines_of_code, comment_lines, blank_lines, lines_of_code_per_language

        def process_and_collect(args):
            file_path, ext = args
            loc, comments, blanks = self.process_file(file_path)
            return loc, comments, blanks, ext

        logging.info(f"Starting to process {len(files_to_process)} files")
        with ThreadPoolExecutor(max_workers=os.cpu_count() * 5) as executor:
            results = executor.map(process_and_collect, files_to_process)

        for loc, comments, blanks, ext in results:
            lines_of_code += loc
            comment_lines += comments
            blank_lines += blanks
            if ext:
                if ext in lines_of_code_per_language:
                    lines_of_code_per_language[ext] += loc
                else:
                    lines_of_code_per_language[ext] = loc

        logging.info(f"Finished processing files. Total LOC: {lines_of_code}, Comments: {comment_lines}, Blanks: {blank_lines}")
        return lines_of_code, comment_lines, blank_lines, lines_of_code_per_language

    def log_common_directories(self):
        try:
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, 'common_directories.log')
            with open(log_file_path, 'a') as log_file:
                log_file.write(f"Repository: {self.repo_name}\n")
                for directory, count in self.directory_counter.most_common():
                    log_file.write(f"{directory}: {count}\n")
                log_file.write("\n")
            logging.info(f"Logged common directories to {log_file_path}")
        except Exception as e:
            logging.error(f"Failed to log common directories: {e}")

    def analyze(self):
        try:
            self.download_and_extract_repo()
            loc, comments, blanks, loc_by_lang = self.count_lines_of_code()
            self.log_common_directories()
        finally:
            shutil.rmtree(self.clone_base_dir, ignore_errors=True)
            logging.info(f"Cleaned up temporary directory {self.clone_base_dir}")
        return {
            'loc': loc,
            'comments': comments,
            'blanks': blanks,
            'locByLangs': loc_by_lang
        }
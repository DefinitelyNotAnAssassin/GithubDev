import os
import shutil
import aiohttp
import aiofiles
import asyncio
import zipfile
import logging
from pathlib import Path
from collections import Counter
import tempfile
import io

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

    async def get_default_branch(self):
        api_url = f"https://api.github.com/repos/{self.username}/{self.repo_name}"
        headers = {}
        token = os.getenv('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = f'token {token}'
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    repo_info = await response.json()
                    default_branch = repo_info.get('default_branch', 'master')
                    logging.info(f"Default branch for {self.username}/{self.repo_name} is {default_branch}")
                    return default_branch
                else:
                    error_message = f"Failed to get repository info: {response.status}"
                    logging.error(error_message)
                    raise Exception(error_message)

    async def download_and_extract_repo(self):
        default_branch = await self.get_default_branch()
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
        async with aiohttp.ClientSession() as session:
            async with session.get(repo_url, headers=headers) as response:
                if response.status == 200:
                    content = await response.read()
                    with zipfile.ZipFile(io.BytesIO(content)) as zip_ref:
                        zip_ref.extractall(self.clone_base_dir)
                    extracted_folder_name = f"{self.repo_name}-{default_branch}"
                    self.clone_dir = os.path.join(self.clone_base_dir, extracted_folder_name)
                    logging.info(f"Extracted repository to {self.clone_dir}")
                else:
                    error_message = f"Failed to download repository: {response.status}"
                    logging.error(error_message)
                    raise Exception(error_message)

    @staticmethod
    async def process_file(file_path):
        lines_of_code = 0
        comment_lines = 0
        blank_lines = 0

        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                async for line in f:
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

    async def count_lines_of_code(self):
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

        async def process_and_collect(file_path, ext):
            loc, comments, blanks = await self.process_file(file_path)
            return loc, comments, blanks, ext

        logging.info(f"Starting to process {len(files_to_process)} files")
        tasks = [process_and_collect(file_path, ext) for file_path, ext in files_to_process]
        results = await asyncio.gather(*tasks)

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

    async def log_common_directories(self):
        try:
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, 'common_directories.log')
            async with aiofiles.open(log_file_path, 'a') as log_file:
                await log_file.write(f"Repository: {self.repo_name}\n")
                for directory, count in self.directory_counter.most_common():
                    await log_file.write(f"{directory}: {count}\n")
                await log_file.write("\n")
            logging.info(f"Logged common directories to {log_file_path}")
        except Exception as e:
            logging.error(f"Failed to log common directories: {e}")

    async def analyze(self):
        try:
            await self.download_and_extract_repo()
            loc, comments, blanks, loc_by_lang = await self.count_lines_of_code()
            await self.log_common_directories()
        finally:
            shutil.rmtree(self.clone_base_dir, ignore_errors=True)
            logging.info(f"Cleaned up temporary directory {self.clone_base_dir}")
        return {
            'loc': loc,
            'comments': comments,
            'blanks': blanks,
            'locByLangs': loc_by_lang
        }
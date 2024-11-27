import os
import shutil
import requests
import io
import zipfile
import logging
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import tempfile
from collections import Counter, defaultdict
from functools import lru_cache
import mmap
import json
import time

# Advanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('repo_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RepoAnalyzer:
    COMMENT_PATTERNS = {
        'python': re.compile(r'^\s*#'),
        'javascript': re.compile(r'^\s*(//|/\*|\*/)'),
        'default': re.compile(r'^\s*[#/]')
    }

    def __init__(self, username, repo_name, ignore_dirs=None, ignore_extensions=None, cache_dir=None):
        """
        Initialize RepoAnalyzer with advanced configuration options.
        
        :param username: GitHub username
        :param repo_name: Repository name
        :param ignore_dirs: Directories to ignore during analysis
        :param ignore_extensions: File extensions to ignore
        :param cache_dir: Directory to store analysis cache
        """
        self.username = username
        self.repo_name = repo_name
        self.repo_url_template = "https://github.com/{username}/{repo_name}/archive/refs/heads/{branch}.zip"
        
        # Use frozenset for immutable, hashable sets
        self.ignore_dirs = frozenset(ignore_dirs or ['.git', '__pycache__', 'node_modules'])
        self.ignore_extensions = frozenset(ignore_extensions or ['.pyc', '.min.js', '.map'])
        
        # Caching setup
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), 'repo_analyzer_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Temporary directory for extraction
        self.clone_base_dir = tempfile.mkdtemp()
        self.clone_dir = self.clone_base_dir
        
        # Advanced counters and tracking
        self.directory_counter = Counter()
        self.file_type_counter = Counter()

    @classmethod
    def _get_comment_pattern(cls, ext):
        """
        Get comment pattern for a given file extension.
        
        :param ext: File extension
        :return: Regex pattern for comments
        """
        return cls.COMMENT_PATTERNS.get(ext[1:], cls.COMMENT_PATTERNS['default'])

    @lru_cache(maxsize=128)
    def get_default_branch(self):
        """
        Cached method to get default branch with more robust error handling.
        
        :return: Default branch name
        """
        cache_file = os.path.join(self.cache_dir, f'{self.username}_{self.repo_name}_branch.json')
        
        # Check cache first
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    if cached_data.get('expiry', 0) > time.time():
                        return cached_data['branch']
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading branch cache: {e}")
        
        api_url = f"https://api.github.com/repos/{self.username}/{self.repo_name}"
        headers = {}
        token = os.getenv('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = f'token {token}'
        
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            repo_info = response.json()
            default_branch = repo_info.get('default_branch', 'master')
            
            # Cache the result
            try:
                with open(cache_file, 'w') as f:
                    json.dump({
                        'branch': default_branch,
                        'expiry': time.time() + 86400  # Cache for 24 hours
                    }, f)
            except IOError as e:
                logger.warning(f"Could not write branch cache: {e}")
            
            return default_branch
        except requests.RequestException as e:
            logger.error(f"Failed to get repository info: {e}")
            return 'master'

    @classmethod
    def process_file(cls, file_info):
        """
        Advanced file processing with memory-mapped file reading and sophisticated line counting.
        
        :param file_info: Tuple of (file path, file extension)
        :return: Tuple of (lines of code, comment lines, blank lines, extension)
        """
        file_path, ext = file_info
        lines_of_code, comment_lines, blank_lines = 0, 0, 0
        
        try:
            # Use memory mapping for more efficient large file reading
            with open(file_path, 'rb') as f:
                mmapped_file = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                
                # Detect comment style based on file extension
                comment_pattern = cls._get_comment_pattern(ext)
                
                for line in iter(mmapped_file.readline, b''):
                    line = line.decode('utf-8', errors='ignore').strip()
                    if not line:
                        blank_lines += 1
                    elif comment_pattern.match(line):
                        comment_lines += 1
                    else:
                        lines_of_code += 1
                
                mmapped_file.close()
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
        
        return lines_of_code, comment_lines, blank_lines, ext

    def count_lines_of_code(self):
        """
        Efficient lines of code counting with parallel processing.
        
        :return: Tuple of (total lines of code, comment lines, blank lines, lines per language)
        """
        files_to_process = []
        for root, dirs, files in os.walk(self.clone_dir):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                ext = Path(file).suffix
                if ext not in self.ignore_extensions:
                    file_path = os.path.join(root, file)
                    files_to_process.append((file_path, ext))
            
            # Update directory and file type counters
            self.directory_counter.update(dirs)
            self.file_type_counter.update(ext for ext in [Path(f).suffix for f in files])

        if not files_to_process:
            return 0, 0, 0, {}

        # Batch processing for better performance
        batch_size = max(1, len(files_to_process) // (os.cpu_count() * 2))
        loc, comments, blanks = 0, 0, 0
        lines_of_code_per_language = defaultdict(int)

        # Use ProcessPoolExecutor for true parallel processing
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            # Submit files in batches
            futures = []
            for i in range(0, len(files_to_process), batch_size):
                batch = files_to_process[i:i+batch_size]
                futures.extend(executor.submit(self.process_file, file_info) for file_info in batch)

            # Process results as they complete
            for future in as_completed(futures):
                try:
                    file_loc, file_comments, file_blanks, ext = future.result()
                    loc += file_loc
                    comments += file_comments
                    blanks += file_blanks
                    lines_of_code_per_language[ext] += file_loc
                except Exception as e:
                    logger.error(f"Error in processing future: {e}")

        return loc, comments, blanks, dict(lines_of_code_per_language)

    def download_and_extract_repo(self):
        """
        Download and extract repository with improved error handling and logging.
        """
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

        try:
            with requests.get(repo_url, headers=headers, stream=True, timeout=30) as response:
                response.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                    zip_ref.extractall(self.clone_base_dir)
            
            extracted_folder_name = f"{self.repo_name}-{default_branch}"
            self.clone_dir = os.path.join(self.clone_base_dir, extracted_folder_name)
            logger.info(f"Repository {self.repo_name} downloaded and extracted successfully")
        except Exception as e:
            logger.error(f"Failed to download or extract repository: {e}")
            raise

    def log_common_directories(self):
        """
        Log common directories with improved error handling and structured logging.
        """
        try:
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, 'common_directories.log')
            
            with open(log_file_path, 'a') as log_file:
                log_file.write(f"Repository: {self.repo_name}\n")
                log_file.write("Common Directories:\n")
                for directory, count in self.directory_counter.most_common(10):
                    log_file.write(f"{directory}: {count}\n")
                
                log_file.write("\n\nFile Types:\n")
                for file_type, count in self.file_type_counter.most_common(10):
                    log_file.write(f"{file_type}: {count}\n")
                
                log_file.write("\n")
            
            logger.info(f"Logged directory and file type statistics for {self.repo_name}")
        except Exception as e:
            logger.error(f"Failed to log common directories: {e}")

    def analyze(self):
        """
        Comprehensive repository analysis with cleanup and result generation.
        
        :return: Dictionary of analysis results
        """
        try:
            logger.info(f"Starting analysis for repository: {self.repo_name}")
            start_time = time.time()
            
            self.download_and_extract_repo()
            loc, comments, blanks, loc_by_lang = self.count_lines_of_code()
            self.log_common_directories()
            
            end_time = time.time()
            logger.info(f"Analysis completed in {end_time - start_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
        finally:
            # Always clean up temporary files
            shutil.rmtree(self.clone_base_dir, ignore_errors=True)
        
        return {
            'loc': loc,
            'comments': comments,
            'blanks': blanks,
            'locByLangs': loc_by_lang,
            'directories': dict(self.directory_counter),
            'fileTypes': dict(self.file_type_counter)
        }

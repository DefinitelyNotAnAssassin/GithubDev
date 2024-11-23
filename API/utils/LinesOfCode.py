import os
import shutil
import subprocess
from pathlib import Path
import tempfile
import platform
import stat
from multiprocessing import Pool, cpu_count

class RepoAnalyzer:
    def __init__(self, username, repo_name, ignore_dirs=None, ignore_extensions=None):
        self.username = username
        self.repo_name = repo_name
        self.repo_url = f"https://github.com/{username}/{repo_name}.git"
        self.ignore_dirs = ignore_dirs if ignore_dirs is not None else []
        self.ignore_extensions = ignore_extensions if ignore_extensions is not None else []
        self.clone_dir = tempfile.mkdtemp()

    def clone_repo(self):
        subprocess.run(["git", "clone", self.repo_url, self.clone_dir], check=True)

    @staticmethod
    def process_file(file_path, ignore_extensions):
        lines_of_code = 0
        comment_lines = 0
        blank_lines = 0
        ext = Path(file_path).suffix
        lines_of_code_per_language = {}

        if ext in ignore_extensions:
            return lines_of_code, comment_lines, blank_lines, lines_of_code_per_language

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                stripped_line = line.strip()
                if not stripped_line:
                    blank_lines += 1
                elif stripped_line.startswith(('#', '//', '/*', '*', '*/')):
                    comment_lines += 1
                else:
                    lines_of_code += 1
                    if ext in lines_of_code_per_language:
                        lines_of_code_per_language[ext] += 1
                    else:
                        lines_of_code_per_language[ext] = 1

        return lines_of_code, comment_lines, blank_lines, lines_of_code_per_language

    def count_lines_of_code(self):
        lines_of_code = 0
        comment_lines = 0
        blank_lines = 0
        lines_of_code_per_language = {}

        files_to_process = []
        for root, dirs, files in os.walk(self.clone_dir):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            for file in files:
                file_path = os.path.join(root, file)
                files_to_process.append(file_path)

        with Pool(cpu_count()) as pool:
            results = pool.starmap(self.process_file, [(file, self.ignore_extensions) for file in files_to_process])

        for loc, comments, blanks, loc_by_lang in results:
            lines_of_code += loc
            comment_lines += comments
            blank_lines += blanks
            for lang, count in loc_by_lang.items():
                if lang in lines_of_code_per_language:
                    lines_of_code_per_language[lang] += count
                else:
                    lines_of_code_per_language[lang] = count

        return lines_of_code, comment_lines, blank_lines, lines_of_code_per_language

    @staticmethod
    def on_rm_error(func, path, exc_info):
        if not os.access(path, os.W_OK):
            os.chmod(path, stat.S_IWUSR)
            func(path)
        else:
            raise
        
        
        
    def stop(self):
        shutil.rmtree(self.clone_dir, onerror=self.on_rm_error)

    def analyze(self):
        try:
            self.clone_repo()
            loc, comments, blanks, loc_by_lang = self.count_lines_of_code()
        finally:
            shutil.rmtree(self.clone_dir, onerror=self.on_rm_error)
        return {
            'loc': loc,
            'comments': comments,
            'blanks': blanks,
            'locByLangs': loc_by_lang
}
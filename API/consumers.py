# API/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from API.utils.LinesOfCode import RepoAnalyzer
from Models.models import UserRecord
from API.constants.ExtensionFilters import default_ignore_extensions, default_ignore_dirs
import os
import aiohttp
import logging
import json
import asyncio

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_API_URL = 'https://api.github.com/users/{username}/repos?per_page=100'
MAX_REPOSITORY_SIZE = 150000  # kilobytes

class LinesOfCodeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        self.close()
        pass
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        username = data['username']
        ignore_dirs = set(data.get('ignore_dirs', default_ignore_dirs))
        ignore_extensions = set(data.get('ignore_extensions', default_ignore_extensions))

        try:
            user_record = await UserRecord.objects.filter(username=username).afirst()
            if user_record:
                await self.send(text_data=json.dumps({'type': 'result', 'total_lines_of_code': user_record.lines_of_code, 'lines_of_code_per_language': user_record.lines_of_code_per_language}))
                await self.send(text_data=json.dumps({'type': 'complete'}))
                return

            repositories = await self.get_repo_info(username)
            total_repos = len(repositories)
            processed_repos = 0
            lines_of_code = 0
            lines_of_code_per_language = {}

            for repository in repositories:
                processed_repos += 1
                await self.send_progress(repository, processed_repos, total_repos)
                await asyncio.sleep(0)  # Yield control to the event loop
                if repository['size'] > MAX_REPOSITORY_SIZE or repository['size'] == 0 or repository['fork']:
                    continue

                loc = RepoAnalyzer(username, repository['name'], ignore_dirs, ignore_extensions).analyze()
                lines_of_code += loc.get('loc', 0)
                for lang, count in loc.get('locByLangs', {}).items():
                    lines_of_code_per_language[lang] = lines_of_code_per_language.get(lang, 0) + count

            user_record = UserRecord(
                username=username,
                lines_of_code=lines_of_code,
                lines_of_code_per_language=lines_of_code_per_language,
                repositories=json.dumps(repositories)
            )
            await user_record.asave()
            await self.send(text_data=json.dumps({'type': 'result', 'total_lines_of_code': user_record.lines_of_code, 'lines_of_code_per_language': lines_of_code_per_language}))
            await self.send(text_data=json.dumps({'type': 'complete'}))
        except Exception as e:
            logging.error(f"Error processing user {username}: {e}")
            return 
        
    async def get_repo_info(self, username):
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        async with aiohttp.ClientSession() as session:
            async with session.get(GITHUB_API_URL.format(username=username), headers=headers) as response:
                return await response.json()

    async def send_progress(self, repository, processed_repos, total_repos):
        message = {
            'type': 'progress',
            'repo': repository['name'],
            'processedRepos': processed_repos,
            'totalRepos': total_repos
        }
        logging.debug(f"Sending message: {message}")
        await self.send(text_data=json.dumps(message))
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from Models.models import UserRecord
from API.utils.LinesOfCode import RepoAnalyzer
from API.constants.ExtensionFilters import default_ignore_extensions, default_ignore_dirs
import requests
import json
import time
from asyncio.exceptions import CancelledError
import os
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_API_URL = 'https://api.github.com/users/{username}/repos?per_page=100'
MAX_REPOSITORY_SIZE = 150000 # kilobytes

def get_repo_info(username):
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    print(f"Getting repositories for {username}")
    print(GITHUB_TOKEN)
    response = requests.get(GITHUB_API_URL.format(username=username), headers=headers)
    return response.json()

def getExtensions(request):
    return JsonResponse({
        'ignore_extensions': list(default_ignore_extensions),
        'ignore_dirs': list(default_ignore_dirs)
    }, status=200)

def getLeaderboard(request):
    page = int(request.GET.get('page', 1))
    users = UserRecord.objects.order_by('-lines_of_code')[(page - 1) * 10: page * 10]
    count = UserRecord.objects.count()
    
    users_list = [
        {
            'username': user.username,
            'lines_of_code': user.lines_of_code,
            'lines_of_code_per_language': user.lines_of_code_per_language
        } for user in users
    ]
    
    return JsonResponse({'users': users_list, 'count': count}, status=200)


def refreshAccountData(request, username):
    UserRecord.objects.filter(username=username).delete() 
    return JsonResponse({'message': 'Data deleted'}, status=200)


    def stream_response():
        try:
            user_record = UserRecord.objects.filter(username=username).first()
            if user_record:
                yield f"event: message\ndata: {json.dumps({'type': 'result', 'total_lines_of_code': user_record.lines_of_code, 'lines_of_code_per_language': user_record.lines_of_code_per_language})}\n\n"
                yield "event: message\ndata: Success\n\n"
                return

            repositories = get_repo_info(username)
            total_repos = len(repositories)
            processed_repos = 0
            lines_of_code = 0
            lines_of_code_per_language = {}

            loc = {}
            for repository in repositories:
                try:
                    print(f"Processing repository {repository['name']}\n\n\n")
                    processed_repos += 1
                    yield f"event: message\ndata: {{\"type\": \"progress\", \"repo\": \"{repository['name']}\", \"processedRepos\": {processed_repos}, \"totalRepos\": {total_repos}}}\n\n"
       
       
                    # Prevent empty or large repositories from being processed
                    if repository['size'] > MAX_REPOSITORY_SIZE or repository['size'] == 0 or repository['fork'] == True:
                        yield f"event: message\ndata: {{\"type\": \"error\", \"message\": \"Repository {repository['name']} is too large\"}}\n\n"
                        yield f"event: message\ndata: {{\"type\": \"progress\", \"repo\": \"{repository['name']}\", \"processedRepos\": {processed_repos}, \"totalRepos\": {total_repos}}}\n\n"
                        continue

                    loc = RepoAnalyzer(username, repository['name'], ignore_dirs, ignore_extensions).analyze()
                    lines_of_code += loc.get('loc', 0)

                    for lang, count in loc.get('locByLangs', {}).items():
                        lines_of_code_per_language[lang] = lines_of_code_per_language.get(lang, 0) + count

                except CancelledError:
                    print("Connection reset by peer")
                    return

            user_record = UserRecord(
                username=username,
                lines_of_code=lines_of_code,
                lines_of_code_per_language=lines_of_code_per_language,
                repositories=json.dumps(repositories)
            )
            user_record.save()
            yield f"event: message\ndata: {json.dumps({'type': 'result', 'total_lines_of_code': user_record.lines_of_code, 'lines_of_code_per_language': lines_of_code_per_language})}\n\n"
            yield f"event: message\ndata: {json.dumps({'type': 'complete'})} \n\n"
            
        except CancelledError:
            return
        except Exception as e:
            yield f"event: message\ndata: {{\"type\": \"error\", \"message\": \"{str(e)}\"}}\n\n"

    response = StreamingHttpResponse(stream_response(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response
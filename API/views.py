from django.shortcuts import render 
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from Models.models import UserRecord     
import requests
import json

def get_repo_info(username): 
    headers = {
        'Authorization': 'token '
    }
    
    response = requests.get(f'https://api.github.com/users/{username}/repos?per_page=100', headers=headers)
    return response.json()


def get_repo_loc(username, repo_name):
    url = f'https://ghloc.ifels.dev/{username}/{repo_name}/master'
    response = requests.get(url)
    try:
        return response.json() 
    except json.decoder.JSONDecodeError: 
        print(response.text)
        return {}


def getLinesOfCode(request, username):
    
    
    def stream_response():
        user_record = UserRecord.objects.filter(username=username).first()
        if user_record:
            yield "event: message\ndata: User already exists\n\n"
            yield f"event: message\ndata: Total lines of code: {user_record.lines_of_code}\n\n"
            yield f"event: message\ndata: Lines of code per language: {json.dumps(user_record.lines_of_code_per_language)}\n\n"
            yield "event: message\ndata: Success\n\n"
            return

        yield "event: message\ndata: User does not exist, processing...\n\n"
        repositories = get_repo_info(username)
        lines_of_code = 0
        lines_of_code_per_language = {}

        for repository in repositories:
            yield f"event: message\ndata: Processing repository: {repository['name']}\n\n"
            loc = get_repo_loc(username, repository['name'])
            lines_of_code += loc.get('loc', 0)

            for lang, count in loc.get('locByLangs', {}).items():
                if lang in lines_of_code_per_language:
                    lines_of_code_per_language[lang] += count
                else:
                    lines_of_code_per_language[lang] = count

        user_record = UserRecord(
            username=username,
            lines_of_code=lines_of_code,
            lines_of_code_per_language=lines_of_code_per_language,
            repositories=json.dumps(repositories)
        )
        user_record.save()
        yield f"event: message\ndata: Total lines of code: {user_record.lines_of_code}\n\n"
        yield f"event: message\ndata: Lines of code per language: {json.dumps(user_record.lines_of_code_per_language)}\n\n"
        yield "event: message\ndata: Success\n\n"

    return StreamingHttpResponse(stream_response(), content_type='text/event-stream')
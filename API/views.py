from django.shortcuts import render 
from django.http import HttpResponse, JsonResponse
from Models.models import UserRecord     
import requests
import json

def get_repo_info(username): 
    headers = {
        'Authorization': 'token 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'
    }
    
    try:
        response = requests.get(f'https://api.github.com/users/{username}/repos?per_page=100', headers=headers)
        return response.json()
    except Exception as e:
        print(e)
        return []


def get_repo_loc(username, repo_name):
    url = f'https://ghloc.ifels.dev/{username}/{repo_name}/master'
    response = requests.get(url)
    try:
        return response.json() 
    except json.decoder.JSONDecodeError: 
        print(response.text)
        return {}
    except Exception as e:
        print(e)
        return {}


def getLinesOfCode(request, username):
    user_record = UserRecord.objects.filter(username=username).first()
    if user_record:
        return JsonResponse({
            "message": "User already exists",
            "total_lines_of_code": user_record.lines_of_code,
            "lines_of_code_per_language": user_record.lines_of_code_per_language,
            "status": "Success"
        })

    repositories = get_repo_info(username)
    lines_of_code = 0
    lines_of_code_per_language = {}

    for repository in repositories:
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

    return JsonResponse({
        "total_lines_of_code": user_record.lines_of_code,
        "lines_of_code_per_language": json.dumps(user_record.lines_of_code_per_language),
        "status": "Success"
    })


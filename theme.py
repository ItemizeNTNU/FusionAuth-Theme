#!/usr/bin/env python3
import requests
from dotenv import load_dotenv
import os
import sys
import json
import pathlib


class Colors:
    """ ANSI color codes """
    BLACK = "\033[0;30m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BROWN = "\033[0;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    LIGHT_GRAY = "\033[0;37m"
    DARK_GRAY = "\033[1;30m"
    LIGHT_RED = "\033[1;31m"
    LIGHT_GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    LIGHT_BLUE = "\033[1;34m"
    LIGHT_PURPLE = "\033[1;35m"
    LIGHT_CYAN = "\033[1;36m"
    LIGHT_WHITE = "\033[1;37m"
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    NEGATIVE = "\033[7m"
    CROSSED = "\033[9m"
    END = "\033[0m"
    # cancel SGR codes if we don't write to a terminal
    if not __import__("sys").stdout.isatty():
        for _ in dir():
            if isinstance(_, str) and _[0] != "_":
                locals()[_] = ""
    else:
        # set Windows console in VT mode
        if __import__("platform").system() == "Windows":
            kernel32 = __import__("ctypes").windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            del kernel32


"""
Simple upload and download script to sync FusionAuth themes with local files for easier tracking in git.
"""

load_dotenv()

TOKEN = os.getenv('FUSION_AUTH_API_TOKEN')
HOST = os.getenv('HOST')
ID = ''
NAME = ''

if os.path.isfile('config.json'):
    with open('config.json') as f:
        config = json.loads(f.read())
        ID = config['id']
        NAME = config['name']


def error(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


for k, v in {'HOST': HOST, 'FUSION_AUTH_API_TOKEN': TOKEN}.items():
    if not v:
        error(f'{k} environment variable is not set!')
        exit(1)


def req(method, path, *args, **kwargs):
    if 'headers' not in kwargs:
        kwargs['headers'] = {}
    kwargs['headers']['Authorization'] = TOKEN
    response = requests.request(method, HOST + path, *args, **kwargs)
    if response.status_code == 401:
        error('Permission denied!')
        error(f'Probably invalid FUSION_AUTH_API_TOKEN or the token does not have access to the {method} {path} endpoint')
        exit(2)
    if response.status_code // 100 != 2:
        error('Request error!')
        kwargs['headers']['Authorization'] = '--REDACTED--'
        error(method, path, [*args], {**kwargs})
        error('Status:', response.status_code)
        error(response.text)
        exit(8)
    return response


def mkdirs(path):
    if not path.is_dir():
        mkdirs(path.parent)
        path.mkdir()


def pull(id):
    """
    Download a theme by id. This will overwrite any local files or changes.
    """
    id = id or ID
    if not id:
        error("Missing id! Seems you have not pullet an initial theme with and id in ./config.json or that the id is valid/missing.")
        error(f'Try using "{sys.argv[0]} pull <id>" as an initial pull instead.')
        error(f'Get a list of available ids with "{sys.argv[0]} list"')
        exit(5)
    data = req('GET', '/api/theme')
    for theme in data.json()['themes']:
        if theme['id'] != id:
            continue

        config = {}
        files = {}
        for k in ['id', 'name']:
            config[k] = theme[k]
        for k in ['defaultMessages', 'stylesheet']:
            files[k] = theme[k] if k in theme else ''
        for folder in ['localizedMessages', 'templates']:
            if folder in theme:
                for k, v in theme[folder].items():
                    files[f'{folder}/{k}'] = v
        for k, v in config.items():
            print(f'{k}: {v}')

        print()

        files['config.json'] = json.dumps(config)
        for k, v in files.items():
            print('Writing file', k)
            mkdirs(pathlib.Path(k).parent)
            with open(k, 'w') as f:
                f.write(v)

        return
    error(f'No theme with id "{id}" found.')
    exit(4)


def push():
    """
    Push all files up to fusion auth
    """
    old_theme = req('GET', f'/api/theme/{ID}').json()['theme']
    for k in ['id', 'insertInstant', 'lastUpdateInstant']:
        del old_theme[k]
    theme = {}
    if not ID or not NAME:
        error('Missing "id" or "name" in config.json. Consider pulling a theme first.')
        exit(6)
    for folder in ['templates', 'localizedMessages']:
        if os.path.isdir(folder):
            theme[folder] = {}
            for template in os.listdir(folder):
                with open(f'{folder}/{template}') as content:
                    theme[folder][template] = content.read()
    theme['name'] = NAME
    for file in ['defaultMessages', 'stylesheet']:
        with open(file) as content:
            theme[file] = content.read()

    def flat_map(map, prefix=''):
        m = {}
        for k, v in map.items():
            if type(v) == dict:
                m.update(flat_map(v, f'{k}.'))
            else:
                m[prefix + k] = v
        return m

    flat_old = flat_map(old_theme)
    flat_new = flat_map(theme)
    for k in sorted(set(list(flat_old.keys()) + list(flat_new.keys()))):
        c, m = '', ''
        if k not in flat_old:
            c, m = Colors.GREEN, 'ADDED'
        elif k not in flat_new:
            c, m = Colors.RED, 'REMOVED'
        elif flat_old[k] != flat_new[k]:
            c, m = Colors.YELLOW, 'UPDATED'
        else:
            m = 'SAME'
        print(f'{c}{k}: {m}{Colors.END}')

    print()
    """Force push
    if input('Confirm push [y/N]: ').lower() not in ['y', 'yes']:
        error('Canceled by user input')
        exit(7)
    """
    req('PUT', f'/api/theme/{ID}', json={'theme': theme})
    print('Theme pushed.')


def list_themes():
    data = req('GET', '/api/theme')
    for theme in data.json()['themes']:
        print(theme['id'], theme['name'])


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        error('Usage:')
        error(f'    {sys.argv[0]} push        -  Push a theme to HOST')
        error(f'    {sys.argv[0]} pull        -  Pull a theme with id from settings.json from HOST')
        error(f'    {sys.argv[0]} pull <id>   -  Pull a theme with id <id> from HOST')
        error(f'    {sys.argv[0]} list        -  List available themes on HOST')
        exit(3)

    if sys.argv[1] == 'push':
        push()
    elif sys.argv[1] == 'pull':
        id = None
        if len(sys.argv) > 2:
            id = sys.argv[2]
        pull(id)
    elif sys.argv[1] == 'list':
        list_themes()
    else:
        error(f'Unknown action "{sys.argv[1]}"')

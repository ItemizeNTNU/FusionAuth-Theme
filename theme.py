#!/usr/bin/env python3
from core import req, mkdirs, print, error, Colors, flat_map, write_files, confirm
import sys
import json
import os

ID = ''
NAME = ''

if os.path.isfile('config.json'):
    with open('config.json') as f:
        config = json.loads(f.read())
        ID = config['id']
        NAME = config['name']


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

        write_files(files)

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

    flat_old = flat_map(old_theme)
    flat_new = flat_map(theme)
    for k in sorted(set(list(flat_old.keys()) + list(flat_new.keys()))):
        c, m = '', ''
        if k not in flat_old:
            c, m = Colors.NORMAL + Colors.GREEN, 'ADDED'
        elif k not in flat_new:
            c, m = Colors.NORMAL + Colors.RED, 'REMOVED'
        elif flat_old[k] != flat_new[k]:
            c, m = Colors.NORMAL + Colors.YELLOW, 'UPDATED'
        else:
            m = 'SAME'
        print(f'{c}{k}: {m}{Colors.END}')

    print()
    confirm('theme push')
    req('PUT', f'/api/theme/{ID}', json={'theme': theme})
    print('Theme pushed.')


def list_themes():
    data = req('GET', '/api/theme')
    for theme in data.json()['themes']:
        print(theme['id'], theme['name'])


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        error('Usage:')
        error(f'    {sys.argv[0]} push        -  Push a theme to HOST. Add -y or --yes to not confirm.')
        error(f'    {sys.argv[0]} pull        -  Pull a theme with id from settings.json from HOST.')
        error(f'    {sys.argv[0]} pull <id>   -  Pull a theme with id <id> from HOST.')
        error(f'    {sys.argv[0]} list        -  List available themes on HOST.')
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

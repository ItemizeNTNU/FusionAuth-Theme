import requests
from dotenv import load_dotenv
import os
import sys
import json
import pathlib


class Colors:
    """ ANSI color codes """
    BLACK = '30m'
    RED = '31m'
    GREEN = '32m'
    YELLOW = '33m'
    BLUE = '34m'
    PURPLE = '35m'
    CYAN = '36m'
    WHITE = '37m'
    NORMAL = '\033[0;'
    BOLD = '\033[1;'
    FAINT = '\033[2;'
    ITALIC = '\033[3;'
    UNDERLINE = '\033[4;'
    BLINK = '\033[5;'
    NEGATIVE = '\033[7;'
    CROSSED = '\033[9;'
    END = '\033[0m'
    # cancel SGR codes if we don't write to a terminal
    if not __import__('sys').stdout.isatty():
        for _ in dir():
            if isinstance(_, str) and _[0] != '_':
                locals()[_] = ''
    else:
        # set Windows console in VT mode
        if __import__('platform').system() == 'Windows':
            kernel32 = __import__('ctypes').windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            del kernel32

    def test():
        colors = ['black', 'red', 'green', 'yellow', 'blue', 'purple', 'cyan', 'white']
        modes = ['normal', 'bold', 'faint', 'italic', 'underline', 'blink', 'negative', 'crossed']
        col1 = max(len(c) for c in colors)
        col2 = max(len(m) for m in modes)
        width = col1 + col2 + 1
        for color in colors:
            c = Colors.__dict__[color.upper()]
            cname = color[0].upper() + color[1:].lower()
            for mode in modes:
                m = Colors.__dict__[mode.upper()]
                mname = mode[0].upper() + mode[1:].lower()
                print(f'{m}{c}{(mname + " " + cname):<{width}}{Colors.END}  ', prefix='', end='')
            print()


"""
Simple upload and download script to sync FusionAuth themes with local files for easier tracking in git.
"""

load_dotenv()

TOKEN = os.getenv('FUSION_AUTH_API_TOKEN')
HOST = os.getenv('HOST')
_print_orig = print


def print(*args, **kwargs):
    kwargs = {
        'sep': ' ',
        'prefix': '[' + Colors.BOLD + Colors.BLUE + '*' + Colors.END + '] ',
        **kwargs
    }
    msg = kwargs['sep'].join(arg if type(arg) == str else repr(arg) for arg in args)
    if msg:
        msg = kwargs['prefix'] + ('\n' + kwargs['prefix']).join(msg.split('\n'))
    del kwargs['prefix']
    _print_orig(msg, **kwargs)


def error(*args, **kwargs):
    print(*args, prefix='[' + Colors.BOLD + Colors.RED + '*' + Colors.END + '] ' + Colors.NORMAL + Colors.RED, end=Colors.END + '\n', **kwargs, file=sys.stderr)


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


def write_files(files):
    for k, v in files.items():
        print('Writing file', k)
        mkdirs(pathlib.Path(k).parent)
        with open(k, 'w') as f:
            f.write(v)


def flat_map(map, prefix=''):
    m = {}
    for k, v in map.items():
        if type(v) == dict:
            m.update(flat_map(v, f'{k}.'))
        else:
            m[prefix + k] = v
    return m


def confirm(msg):
    print(f'Confirm {msg} [y/N]: ', end='')
    if '-y' in sys.argv or '--yes' in sys.argv:
        print('--yes', prefix='')
    elif input().lower() not in ['y', 'yes']:
        error('Canceled by user input')
        exit(7)


if __name__ == '__main__':
    print('Color Test:')
    Colors.test()

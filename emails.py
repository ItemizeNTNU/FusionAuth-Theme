from core import error, print, req, mkdirs, write_files, Colors, confirm
import sys
import os
import json


def save_to_disk(dirname, id, name, subject, html, txt, new=True):
    path = f'emailTemplates/{dirname}'
    if new and os.path.isdir(path):
        error(f"Email '{dirname}' already exists")
        exit(9)
    settings = {
        'id': id,
        'name': name,
        'subject': subject,
    }
    files = {
        f'{path}/settings.json': json.dumps(settings, indent=4, sort_keys=True),
        f'{path}/template.html': html,
        f'{path}/template.txt': txt
    }
    write_files(files)


def upload(id, name, subject, html, txt, create=False, save_non_id_dirname=None):
    if id:
        id = '/' + id
	else:
        create = True
    res = req('POST' if create else 'PUT', '/api/email/template' + id, json={
        'emailTemplate': {
            'name': name,
            'defaultSubject': subject,
            'defaultHtmlTemplate': html,
            'defaultTextTemplate': txt,
        }
    })
    if save_non_id_dirname and not id:
        save_to_disk(save_non_id_dirname, id, name, subject, html, txt)
    return res.json()['emailTemplate']


def read_email_file(dirname, path):
    with open(f'emailTemplates/{dirname}/{path}') as file:
        return file.read()


def read_disk(dirname):
    settings = json.loads(read_email_file(dirname, 'settings.json'))
    settings['html'] = read_email_file(dirname, 'template.html')
    settings['txt'] = read_email_file(dirname, 'template.txt')
    return settings


def is_same(local, remote):
    r = {'subject': 'defaultSubject', 'html': 'defaultHtmlTemplate', 'txt': 'defaultTextTemplate'}
    diff = []
    for k, v in local.items():
        if v != remote[r.get(k, k)]:
            diff.append(k)
    return diff


def status():
    local = {email: read_disk(email) for email in os.listdir('emailTemplates/') if os.path.isdir(f'emailTemplates/{email}')}
    remote = list_emails(_print=False)
    col = max(len(name)for name in local.keys())
    def name_conflict(name): return name in [email['name'] for email in remote.values()]
    for name, email in sorted(local.items()):
        c, m = '', ''
        if email['id'] not in remote:
            if name_conflict(name):
                if not email['id']:
                    c, m = Colors.NORMAL + Colors.RED, 'NAME CONFLICT (missing local id)'
                else:
                    c, m = Colors.NORMAL + Colors.RED, 'NAME CONFLICT (local and remote id differ)'
            elif not email['id']:
                c, m = Colors.NORMAL + Colors.GREEN, 'CREATE (generate id)'
            else:
                c, m = Colors.NORMAL + Colors.GREEN, 'CREATE (missing remote)'
        elif len(diff := is_same(email, remote[email['id']])) == 0:
            m = 'SAME'
        else:
            c, m = Colors.NORMAL + Colors.YELLOW, f'UPDATED ({", ".join(diff)})'
        print(f'{c}{name:<{col}} : {m}{Colors.END}')
    return local, remote


def push():
    local, remote = status()
    print()
    confirm('email push')
    for dirname, email in local.items():
        create = email['id'] not in remote
        upload(**email, create=create, save_non_id_dirname=dirname)
    print(f'{len(local)} email templates pushed.')


def download(id, name=''):
    res = req('GET', f'/api/email/template/{id}')
    email = res.json()['emailTemplate']
    save_to_disk(name or email['name'], id, email['name'], email['defaultSubject'], email['defaultHtmlTemplate'], email['defaultTextTemplate'])


def create(name):
    email = upload('', name, 'This is the subject', '<p>This is the html</p>', 'This is the plain text')
    save_to_disk(name, email['id'], name, email['defaultSubject'], email['defaultHtmlTemplate'], email['defaultTextTemplate'])


def list_emails(_print=True):
    res = req('GET', '/api/email/template')
    emails = {}
    for email in res.json()['emailTemplates']:
        if _print:
            print(email['id'], '-', email['name'])
        emails[email['id']] = email
    return emails


def delete(id):
    res = req('DELETE', f'/api/email/template/{id}')
    print(f'Successfully deleted email template with id {id}')


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        error('Usage:')
        error(f'    {sys.argv[0]} status                 -  Print email template statuses.')
        error(f'    {sys.argv[0]} push                   -  Push email templates. Add -y or --yes to not confirm.')
        error(f'    {sys.argv[0]} pull                   -  Pull all downloaded email templates.')
        error(f'    {sys.argv[0]} download <id> [name]   -  Pull an email template with id <id> from HOST to directory emailTemplates/<name>.')
        error(f'    {sys.argv[0]} create <name>          -  Create a new email template at HOST in directory emailTemplates/<name>.')
        error(f'    {sys.argv[0]} delete <id>            -  Delete a remote email template. Add -y or --yes to not confirm.')
        error(f'    {sys.argv[0]} list                   -  List available email templates.')
        exit(3)

    if sys.argv[1] == 'status':
        status()
    elif sys.argv[1] == 'push':
        push()
    elif sys.argv[1] == 'pull':
        pull()
    elif sys.argv[1] == 'download':
        download(*sys.argv[2:3+1])
    elif sys.argv[1] == 'create':
        create(sys.argv[2])
    elif sys.argv[1] == 'delete':
        delete(sys.argv[2])
    elif sys.argv[1] == 'list':
        list_emails()
    else:
        error(f'Unknown action "{sys.argv[1]}"')

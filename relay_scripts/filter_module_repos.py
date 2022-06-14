#!/usr/bin/env python
from relay_sdk import Interface, Dynamic as D

relay = Interface()

modules = []
for repo in relay.get(D.repositories):
    try:
        if 'module' in repo['topics']:
            modules.append('puppetlabs/{0}'.format(repo['name']))

    except Exception as e:
        print('Could not process https://github.com/puppetlabs/{0}'.format(repo['name']))

relay.outputs.set('module_repos', modules)

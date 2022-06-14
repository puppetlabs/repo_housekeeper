#!/usr/bin/env python
from relay_sdk import Interface, Dynamic as D

relay = Interface()

modules = []
unsupported == []
for repo in relay.get(D.repositories):
    try:
        if 'module' in repo['topics']:
            full_name = f'puppetlabs/{repo['name']}'
            modules.append(full_name)
            if not 'supported' in repo['topics']:
                unsupported.append(full_name)

    except Exception as e:
        print('Could not process https://github.com/puppetlabs/{0}'.format(repo['name']))

relay.outputs.set('module_repos', modules)
relay.outputs.set('unsupported_module_repos', unsupported)

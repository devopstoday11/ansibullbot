#!/usr/bin/env python

from lib.utils.systemtools import *

class ModuleIndexer(object):

    def __init__(self):
        self.modules = {}
        self.checkoutdir = '/tmp/ansible.modules.checkout'

    def create_checkout(self):
        """checkout ansible"""
        cmd = "git clone http://github.com/ansible/ansible --recursive %s" % self.checkoutdir
        (rc, so, se) = run_command(cmd)
        print str(so) + str(se)

    def update_checkout(self):
        """rebase + pull + update the checkout"""
        cmd = "cd %s ; git pull --rebase" % self.checkoutdir
        (rc, so, se) = run_command(cmd)
        print str(so) + str(se)
        cmd = "cd %s ; git submodule update --recursive" % self.checkoutdir
        (rc, so, se) = run_command(cmd)
        print str(so) + str(se)

    def _find_match(self, pattern):
        '''
        if pattern == 'docker':
            pattern = 'lib/ansible/modules/core/cloud/docker/_docker.py'
            return self.modules[pattern]
        '''

        match = None
        for k,v in self.modules.iteritems():
            if v['name'] == pattern:
                match = v
                break
        if not match:
            # search by key ... aka the filepath
            for k,v in self.modules.iteritems():
                if k == pattern:
                    match = v
                    break
        if not match:
            # search by properties
            for k,v in self.modules.iteritems():
                for subkey in v.keys():
                    if v[subkey] == pattern:
                        match = v
                        break
                if match:
                    break
        return match

    def find_match(self, pattern):
        #if pattern == 'docker':
        #    import epdb; epdb.st()
        if not pattern:
            return None
        match = self._find_match(pattern)
        if not match:
            # check for just the basename
            #   2617: ansible-s-extras/network/cloudflare_dns.py
            bname = os.path.basename(pattern)
            match = self._find_match(bname)

            if not match:
                # check for deprecated name
                #   _fireball -> fireball
                match = self._find_match('_' + bname)

        return match

    def is_valid(self, mname):
        match = self.find_match(mname)
        if match:
            return True
        else:
            return False

    def get_repository_for_module(self, mname):
        match = self.find_match(mname)
        if match:
            return match['repository']
        else:
            return None

    def get_ansible_modules(self):
        """Make a list of known modules"""

        # manage the checkout
        if not os.path.isdir(self.checkoutdir):
            self.create_checkout()
        else:
            self.update_checkout()

        #(Epdb) pp module
        #u'wait_for'
        #(Epdb) pp self.module_indexer.is_valid(module)
        #False        

        matches = []
        module_dir = os.path.join(self.checkoutdir, 'lib/ansible/modules')
        module_dir = os.path.expanduser(module_dir)
        for root, dirnames, filenames in os.walk(module_dir):
            for filename in filenames:
                if 'lib/ansible/modules' in root \
                    and not filename == '__init__.py' \
                    and (filename.endswith('.py') or filename.endswith('.ps1')):
                    matches.append(os.path.join(root, filename))    

        matches = sorted(set(matches))

        # figure out the names
        for match in matches:
            mdict = {}

            mdict['filename'] = os.path.basename(match)

            dirpath = os.path.dirname(match)
            dirpath = dirpath.replace(self.checkoutdir + '/', '')
            mdict['dirpath'] = dirpath

            filepath = match.replace(self.checkoutdir + '/', '')
            mdict['filepath'] = filepath

            subpath = dirpath.replace('lib/ansible/modules/', '')
            path_parts = subpath.split('/')
            mdict['repository'] = path_parts[0]
            mdict['topic'] = path_parts[1]
            if len(path_parts) > 2:
                mdict['subtopic'] = path_parts[2]
                mdict['fulltopic'] = '/'.join(path_parts[1:3]) + '/'
            else:
                mdict['subtopic'] = None
                mdict['fulltopic'] = path_parts[1] +'/'

            mdict['repo_filename'] = mdict['filepath']\
                .replace('lib/ansible/modules/%s/' % mdict['repository'], '')

            # clustering/consul
            mdict['namespaced_module'] = mdict['repo_filename']
            mdict['namespaced_module'] = mdict['namespaced_module']\
                                            .replace('.py', '')
            mdict['namespaced_module'] = mdict['namespaced_module']\
                                            .replace('.ps1', '')

            mname = os.path.basename(match)
            mname = mname.replace('.py', '')
            mname = mname.replace('.ps1', '')
            mdict['name'] = mname

            # deprecated modules
            if mname.startswith('_'):
                deprecated_filename = \
                    os.path.dirname(mdict['namespaced_module'])
                deprecated_filename = \
                    os.path.join(deprecated_filename, mname[1:] + '.py')
                mdict['deprecated_filename'] = deprecated_filename
            else:
                mdict['deprecated_filename'] = mdict['repo_filename']

            #if 'fireball' in match:
            #    import epdb; epdb.st()

            mkey = mdict['filepath']
            self.modules[mkey] = mdict

        # meta is a special module
        self.modules['meta'] = {}
        self.modules['meta']['name'] = 'meta'
        self.modules['meta']['namespaced_module'] = None
        self.modules['meta']['deprecated_filename'] = None
        self.modules['meta']['dirpath'] = None
        self.modules['meta']['filename'] = None
        self.modules['meta']['filepath'] = None
        self.modules['meta']['fulltopic'] = None
        self.modules['meta']['repo_filename'] = 'meta'
        self.modules['meta']['repository'] = 'core'
        self.modules['meta']['subtopic'] = None
        self.modules['meta']['topic'] = None

        # deprecated modules are annoying
        newitems = []
        for k,v in self.modules.iteritems():
            if v['name'].startswith('_'):
                dkey = os.path.dirname(v['filepath'])
                dkey = os.path.join(dkey, v['filename'].replace('_', '', 1))
                if not dkey in self.modules:
                    nd = v.copy()
                    nd['name'] = nd['name'].replace('_', '', 1)
                    newitems.append((dkey, nd))
        for ni in newitems:
            self.modules[ni[0]] = ni[1]
        #import epdb; epdb.st()

        return self.modules



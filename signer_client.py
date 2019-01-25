#!/usr/bin/python

import sys
import os
import re
import copy
import argparse
import uuid
import httplib
import msvcrt
import time
from datetime import datetime


__all__ = ['sign', 'sign_impl', 'getcerts']

################################################################################
# Global configuration

# Command line arguments
cmdlineArgs = {}
# Signer server URL
signerAddr = '10.28.28.192:8765'
# URL of the SHA-1 timestamp server
tsURL_sha1 = 'http://timestamp.digicert.com/'
# URL of the SHA-256 timestamp server
tsURL_sha2 = 'http://timestamp.digicert.com/'

# Alternative URLs
#tsURL_sha1 = 'http://timestamp.globalsign.com/scripts/timestamp.dll'
#tsURL_sha2 = 'http://rfc3161timestamp.globalsign.com/advanced'


################################################################################
# Auxiliary functions

def dbg_print(s):
    global cmdlineArgs
    if not cmdlineArgs.debug:
        return
    sys.stdout.flush()
    print s
    sys.stdout.flush()

lockfile = __file__ + '.lock'
lockfh = None

# Starts critical section for multiprocess sync; waits infinitely until the lock is acquired
# Input:
#   filepath - file name being processed in the CS (used for debugging prints only)
# Output:
#   None
def cs_enter(filepath):
    global cmdlineArgs, lockfile, lockfh
    if cmdlineArgs.skip_lock:
        return
    dbg_print('SIGNLOCK: cs_enter on file %s' % (filepath))
    lockfh = open(lockfile, 'w')
    while True:
        try:
            msvcrt.locking(lockfh.fileno(), msvcrt.LK_NBRLCK, 1)
            dbg_print('SIGNLOCK: lock acquired on file %s' % (filepath))
            break
        except IOError:
            time.sleep(1)

# Exits the critical section
# Input:
#   filepath - file name being processed in the CS (used for debugging prints only)
# Output:
#   None
def cs_leave(filepath):
    global cmdlineArgs, lockfile, lockfh
    if cmdlineArgs.skip_lock:
        return
    dbg_print('SIGNLOCK: cs_leave on file %s' % (filepath))
    msvcrt.locking(lockfh.fileno(), msvcrt.LK_UNLCK, 1)
    dbg_print('SIGNLOCK: unlocked file %s' % (filepath))
    lockfh.close()
    dbg_print('SIGNLOCK: closed lock on file %s' % (filepath))
    lockfh = None

# Creates HTTP POST request body from the specified fields.
# Input:
#   fields   - dictionary of fieldname:value for string values
#   files    - dictionary of fieldname:path-to-file for files
#   boundary - string used as multipart delimiter
# Output:
#   Formatted request body contents.
def encode_multipart_formdata(fields, files, boundary):
    lines = []
    for (fieldname, value) in fields.iteritems():
        lines.append('--' + boundary)
        lines.append('Content-Disposition: form-data; name="%s"' % fieldname)
        lines.append('')
        lines.append(value)
    for (fieldname, filepath) in files.iteritems():
        # Normally we work with small files, so keeping the full request body in memory is not a problem.
        # If large files support is required, all this needs to be redesigned to use streamed read-write.
        lines.append('--' + boundary)
        lines.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (fieldname, os.path.basename(filepath)))
        lines.append('Content-Type: application/octet-stream')
        lines.append('')
        lines.append(open(filepath, 'rb').read())
    lines.append('--' + boundary + '--')
    lines.append('')
    return '\r\n'.join(lines)

################################################################################
# Exported functions

# User-friendly implementation for signing a file.
# It translates the selected hash algorithm into command line arguments and
# adds the timestamping using the default predefined URLs. Otherwise, it's
# the same as sign_impl().
# Input:
#   basic_params - (list) sequence of dicts, each with parameters for single signing:
#       cert     - (str) thumbprint of the certificate to sign with
#       passwd   - (str) password for the selected certificate's token
#       cross    - (bool) whether to use cross-certificate
#       hash     - (str) hash algorithm for signature (sha1 or sha2)
#       args     - (list) list of additional arguments for signtool
#   filepath     - (str) path to the file to be signed, will be replaced
# Output:
#   True if signing was successful; False otherwise. Error message (if any) is
#   printed to standard output.
def sign(basic_params, filepath):
    sign_params = copy.deepcopy(basic_params)
    for sp in sign_params:
        if sp['hash'] == 'sha1':
            sp['args'] += ['/fd', 'sha1', '/t', tsURL_sha1]
        else:
            sp['args'] += ['/fd', 'sha256', '/td', 'sha256', '/tr', tsURL_sha2]
    return sign_impl(sign_params, filepath)

# Low-level signing function that represents a front-end for the HTML form procided by the signer server.
# Input:
#   sign_params - (list) sequence of dicts, each with parameters for single signing:
#       cert    - (str) thumbprint of the certificate to sign with
#       passwd  - (str) password for the selected certificate's token
#       cross   - (bool) whether to use cross-certificate
#       args    - (list) list of arguments for signtool
#   filepath    - (str) path to the file to be signed, will be replaced
# Output:
#   True if signing was successful; False otherwise. Error message (if any) is
#   printed to standard output.
def sign_impl(sign_params, filepath):
    global cmdlineArgs
    # Prepare list of fields for formatting multipart body
    fields = {}
    for i in range(len(sign_params)):
        fields.update({
            'cert%d'   % i : sign_params[i]['cert'],
            'passwd%d' % i : sign_params[i]['passwd'],
            'args%d'   % i : ' '.join(map(lambda s: ('"' + s + '"'), sign_params[i]['args'])),
            'cross%d'  % i : 'on' if sign_params[i]['cross'] else 'off'
        })
    files = {'filedata': filepath}

    res = False
    cs_enter(filepath)
    try:
        # Random boundary that will hardly appear in our data
        boundary = '----------' + uuid.uuid4().hex
        req_body = encode_multipart_formdata(fields, files, boundary)
        conn = httplib.HTTPConnection(signerAddr, timeout = cmdlineArgs.timeout)
        conn.request('POST', '/', req_body, {'Content-Type': 'multipart/form-data; boundary=%s' % boundary})
        response = conn.getresponse()
        if response.status == httplib.OK:
            # File signed, save it under the same name overwriting the original
            with open(filepath, 'wb') as f:
                f.write(response.read())
            print 'File ' + filepath + ' was signed successfully.'
            res = True
        else:
            # Something went wrong; print what server has to tell about this
            data = response.read()
            print response.status, response.reason
            print data
        conn.close()
    except IOError, e:
        print "File input/output problem: %s" % (e.strerror)
    except httplib.HTTPException, e:
        print "Connection problem: %s" % (e)
    cs_leave(filepath)
    return res

# Lists all available certificates from the signer server.
# Input:
#   None
# Output:
#   List of dicts describing each certificate:
#       name       - (str) subject name
#       hash       - (str) hash algorithm
#       thumbprint - (str) thumbprint
#       expiry     - (str) expiration date/time in the format '<year>-<month>-<day>T<hours>:<minutes>:<seconds>'
def getcerts():
    global cmdlineArgs
    conn = httplib.HTTPConnection(signerAddr, timeout = cmdlineArgs.timeout)
    conn.request('GET', '/certlist')
    response = conn.getresponse()
    if response.status == httplib.OK:
        res = []
        re_cert_line = re.compile(r'^(\S+)\s+(.*)\s+\(([a-z0-9/]+)\)\s+\[(\d+-\d+-\d+T\d+:\d+:\d+)[^\[\]]*\]$', re.I)
        for ln in response.read().split("\n"):
            if ln == '':
                continue
            m = re_cert_line.match(ln)
            if not m:
                print "Failed to parse server output: '%s'" % ln
                continue
            res.append({
                'name': m.group(2),
                'hash': m.group(3),
                'thumbprint': m.group(1),
                'expiry': datetime.strptime(m.group(4), '%Y-%m-%dT%H:%M:%S')
            })
    else:
        # Something went wrong; print what server has to tell about this
        print 'Failed to obtain the list of certificates, server returned: %s %s' % (response.status, response.reason)
        print response.read()
        res = None
    conn.close()
    return res


################################################################################
# Command line interface

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest = 'cmd')

    parser.add_argument('--timeout', action = 'store', default = 300, type = int,
                       help = 'Timeout (in seconds) for HTTP operations')
    parser.add_argument('--skip-lock', action = 'store_true',
                       help = 'NOT RECOMMENDED! Allow multiple processes to send requests in parallel.')
    parser.add_argument('--debug', action = 'store_true',
                       help = 'Print some debugging information')

    list_parser = subparsers.add_parser('list', help = 'List available certificates (thumbprint, name, hash algorithm)')

    sign_parser = subparsers.add_parser('sign', help = 'Sign the file')

    sign1 = sign_parser.add_argument_group('First signature')
    sign1.add_argument('--tcert1', action = 'store', required = True,
                       help = 'Thumbprint of the certificate to use')
    sign1.add_argument('--passwd1', action = 'store', required = True,
                       help = 'Token password for the certificate')
    sign1.add_argument('--cross1', action = 'store_true',
                       help = 'Sign with cross-certificate')
    sign1.add_argument('--hash1', action = 'store', choices = ['sha1', 'sha2'],
                       help = 'Algorithm for the signature; default: sha2 for single-sign, sha1 for dual-sign')
    sign1.add_argument('--args1', action = 'append',
                       help = 'Additional arguments (can be supplied multiple times)')

    sign2 = sign_parser.add_argument_group('Second signature (for dual-signing)')
    sign2.add_argument('--tcert2', action = 'store',
                       help = 'Thumbprint of the certificate to use')
    sign2.add_argument('--passwd2', action = 'store',
                       help = 'Token password for the certificate')
    sign2.add_argument('--cross2', action = 'store_true',
                       help = 'Sign with cross-certificate')
    sign2.add_argument('--hash2', action = 'store', choices = ['sha1', 'sha2'], default = 'sha2',
                       help = 'Algorithm for the signature; default: sha2')
    sign2.add_argument('--args2', action = 'append',
                       help = 'Additional arguments (can be supplied multiple times)')

    sign_parser.add_argument('file', nargs = 1,
                             help = 'File to sign (will be replaced)')

    cmdlineArgs = parser.parse_args()
    if cmdlineArgs.cmd == 'list':
        certs = getcerts()
        if certs:
            for c in certs:
                c['expiry_fmt'] = c['expiry'].strftime('%d.%m.%Y %H:%M:%S UTC')
                c['expired'] = ''
                if c['expiry'] < datetime.utcnow():
                    c['expired'] = '[X] '
                print '%(expired)s%(thumbprint)s %(name)s (%(hash)s), valid till: %(expiry_fmt)s' % c
            res = True
        else:
            res = False
    else:
        # Configure the conditional default for hash1
        if not getattr(cmdlineArgs, 'hash1', None):
            if getattr(cmdlineArgs, 'tcert2', None):
                cmdlineArgs.hash1 = 'sha1'
            else:
                cmdlineArgs.hash1 = 'sha2'
        # Prepare parameters for sign()
        basic_params = []
        n = 1
        while True:
            s = {
                'cert'   : getattr(cmdlineArgs, 'tcert%d'  % n, None),
                'passwd' : getattr(cmdlineArgs, 'passwd%d' % n, None),
                'cross'  : getattr(cmdlineArgs, 'cross%d'  % n, False),
                'hash'   : getattr(cmdlineArgs, 'hash%d'   % n, None),
                'args'   : getattr(cmdlineArgs, 'args%d'   % n, None)
            }
            if not s['cert']:
                break
            if not s['passwd']:
                print 'Password for certificate No.%d cannot be empty.' % n
                exit(1)
            if not s['args']:
                s['args'] = []
            basic_params.append(s)
            n += 1

        res = sign(basic_params, cmdlineArgs.file[0])

    exit(0 if res else 1)

#!/usr/bin/python

import sys
import os
import re
import argparse
import uuid
import httplib
import msvcrt
import time

__all__ = ['sign', 'sign_impl', 'getcerts']

################################################################################
# Global configuration

# Signer server URL
signerAddr = '10.28.28.192:8765'
# URL of the SHA-1 timestamp server
tsURL_sha1 = 'http://timestamp.digicert.com/'
# URL of the SHA-256 timestamp server
tsURL_sha2 = 'http://timestamp.digicert.com/'


################################################################################
# Auxiliary functions

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

lockfile = __file__ + '.lock'
lockfh = None
def cs_enter():
    global lockfile, lockfh
    #print 'cs_enter'
    lockfh = open(lockfile, 'w')
    #print 'opened %s' % lockfh
    while True:
        try:
            msvcrt.locking(lockfh.fileno(), msvcrt.LK_NBRLCK, 1)
            #print 'locked'
            break
        except IOError:
            time.sleep(1)

def cs_leave():
    global lockfile, lockfh
    #print 'cs_leave, lfh: %s, file: %s' % (lockfh, lockfile)
    msvcrt.locking(lockfh.fileno(), msvcrt.LK_UNLCK, 1)
    #print 'unlocked'
    lockfh.close()
    #print 'closed'
    lockfh = None

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
    sign_params = basic_params[:]
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
    cs_enter()
    try:
        # Random boundary that will hardly appear in our data
        boundary = '----------' + uuid.uuid4().hex
        req_body = encode_multipart_formdata(fields, files, boundary)
        conn = httplib.HTTPConnection(signerAddr)
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
        print "File input/output problem: " + e.strerror
    except httplib.HTTPException, e:
        print "Connection problem: " + str(e)
    cs_leave()
    return res

# Lists all available certificates from the signer server.
# Input:
#   None
# Output:
#   List of dicts describing each certificate:
#       name       - (str) subject name
#       hash       - (str) hash algorithm
#       thumbprint - (str) thumbprint
def getcerts():
    conn = httplib.HTTPConnection(signerAddr)
    conn.request('GET', '/certlist')
    response = conn.getresponse()
    if response.status == httplib.OK:
        res = []
        re_cert_line = re.compile('^(\S+)\s+(.*)\s+\(([a-z0-9/]+)\)$', re.I)
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
                'thumbprint': m.group(1)
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

    args = parser.parse_args()
    if args.cmd == 'list':
        certs = getcerts()
        if certs:
            for c in certs:
                print '%(thumbprint)s %(name)s (%(hash)s)' % c
            res = True
        else:
            res = False
    else:
        # Configure the conditional default for hash1
        if not getattr(args, 'hash1', None):
            if getattr(args, 'tcert2', None):
                args.hash1 = 'sha1'
            else:
                args.hash1 = 'sha2'
        # Prepare parameters for sign()
        basic_params = []
        n = 1
        while True:
            s = {
                'cert'   : getattr(args, 'tcert%d'  % n, None),
                'passwd' : getattr(args, 'passwd%d' % n, None),
                'cross'  : getattr(args, 'cross%d'  % n, False),
                'hash'   : getattr(args, 'hash%d'   % n, None),
                'args'   : getattr(args, 'args%d'   % n, None)
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

        res = sign(basic_params, args.file[0])

    exit(0 if res else 1)

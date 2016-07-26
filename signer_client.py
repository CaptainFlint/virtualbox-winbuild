#!/usr/bin/python

import sys
import os
import argparse
import uuid
import httplib

__all__ = ['sign', 'sign_impl']

################################################################################
# Global configuration

# Signer server URL
signerAddr = '10.28.28.192:8765'
# Name of the certificate to use for signing
certName = 'Parallels International Gmbh'
# Thumbprint of the certificate
# (in case there are several certificates with the same name)
certThumbprint = 'ce de 1d bd 3f d3 b6 bc c5 dd f6 95 a3 24 4c 7a 38 3f ce 70'
# URL of the SHA-1 timestamp server
tsURL_sha1 = 'http://timestamp.geotrust.com/tsa'
# URL of the SHA-256 timestamp server
tsURL_sha2 = 'http://sha256timestamp.ws.symantec.com/sha256/timestamp'


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

################################################################################
# Signing functions

# User-friendly implementation for signing a file using the most common parameters.
# Input:
#   passwd   - (str) EV token password
#   sha1     - (bool) whether to sign using SHA-1 algorithm
#   sha2     - (bool) whether to sign using SHA-2 algorithm (used by default if
#               both sha1 and sha2 set to False; dual-signing is supported)
#   cross    - (bool) whether to use cross-certificate
#   args     - (array) additional signtool command line arguments
#   filepath - (str) path to the file to be signed, will be replaced
# Output:
#   True if signing was successful; False otherwise. Error message (if any) is
#   printed to standard output.
def sign(passwd, sha1, sha2, cross, args, filepath):
    # Construct list of signtool arguments for sha1/sha2 signing
    params = []
    args_str = ''
    if args:
        for a in args:
            args_str += ' "' + a + '"'
    certThumbprintArg = certThumbprint.replace(' ', '')
    if sha1:
        params.append('/n "%s" /sha1 %s /fd sha1 /td sha1 /tr %s%s' % (certName, certThumbprintArg, tsURL_sha1, args_str))
    if sha2 or (not sha1 and not sha2):
        params.append('/n "%s" /sha1 %s /fd sha256 /td sha256 /tr %s%s' % (certName, certThumbprintArg, tsURL_sha2, args_str))
    if len(params) < 2:
        params.append('')
    return sign_impl(passwd, params[0], cross, params[1], cross, filepath)

# Low-level signing function that represents a front-end for the HTML form procided by the signer server.
# Input:
#   passwd   - (str) EV token password
#   args1    - (str) first list of arguments for signtool (mandatory)
#   cross1   - (bool) whether to use cross-certificate for the first signing
#   args2    - (str) second list of arguments for signtool (optional)
#   cross2   - (bool) whether to use cross-certificate for the second signing
#   filepath - (str) path to the file to be signed, will be replaced
# Output:
#   True if signing was successful; False otherwise. Error message (if any) is
#   printed to standard output.
def sign_impl(passwd, args1, cross1, args2, cross2, filepath):
    # Prepare list of fields for formatting multipart body
    fields = {'passwd': passwd,
              'args':   args1,
              'cross':  'on' if cross1 else 'off',
              'args2':  args2,
              'cross2': 'on' if cross2 else 'off'
             }
    files = {'filedata': filepath}

    res = False
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
    return res


################################################################################
# Command line interface

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', dest='cross', action = 'store_true',
                        help = 'Sign with cross-certificate')
    parser.add_argument('--sha1', action = 'store_true',
                        help = 'Use sha1 signing (may be combined with sha2)')
    parser.add_argument('--sha2', action = 'store_true',
                        help = 'Use sha256 signing (default; may be combined with sha1)')
    parser.add_argument('-p', dest='passwd', action = 'store', required = True,
                        help = 'Token password')
    parser.add_argument('-a', dest='params', action = 'append',
                        help = 'Additional arguments (can be supplied multiple times)')
    parser.add_argument('file', nargs = 1,
                        help = 'File to sign (output will be saved to file with suffix "-signed" added to the name)')
    args = parser.parse_args()
    res = sign(args.passwd, args.sha1, args.sha2, args.cross, args.params, args.file[0])
    exit(0 if res else 1)

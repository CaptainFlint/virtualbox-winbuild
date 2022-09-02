#!/usr/bin/python

import os
import re
import sys
import shutil
import urllib
import time
import urlparse
import httplib
import ssl
import json

workDir = os.path.dirname(os.path.realpath(__file__))

def output(str):
	print str
	sys.stdout.flush()
	sys.stderr.flush()

# Class for managing Microsoft Dashboard API for driver signing
class MsDashboardAPI:
	def __init__(self):
		# Authentication data
		self.authFile = os.path.join(workDir, 'secret', 'microsoft-auth')
		self.auth = dict([re.split(r'\s*=\s*', re.sub(r'[\r\n]+', '', s), 1) for s in open(self.authFile, 'r').readlines()])
		missing = set(('secretKey', 'clientID', 'tenantID')) - set(self.auth.keys())
		if missing:
			raise Exception('The following authentication parameters are missing in %s:\n%s' % (self.authFile, ', '.join(missing)))

		# Authentication URL
		self.authAddr = 'login.microsoftonline.com'
		self.authUrlPath = '/%s/oauth2/token' % (self.auth['tenantID'])

		# Dashboard API URL
		self.resourceAddr = 'manage.devcenter.microsoft.com'
		self.resourceUrl = 'https://' + self.resourceAddr
		self.apiBaseUrlPath = '/v1.0/my/hardware/'

		# Access token
		self._accessToken = None

	# Automatically updates the access token if necessary and returns it
	@property
	def accessToken(self):
		# To be on the safe side, force-expire the token 10 minutes before its end of life
		if not self._accessToken or self._accessToken['expires_on'] < time.time() + 600:
			output('Access token is missing or expired, requesting new access token')
			self._accessToken = self.doRequest(
				method = 'POST',
				addr = self.authAddr,
				path = self.authUrlPath,
				data = urllib.urlencode({
					'grant_type': 'client_credentials',
					'client_id': self.auth['clientID'],
					'client_secret': self.auth['secretKey'],
					'resource': self.resourceUrl
				}),
				headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'},
				useAuth = False
			)
		if self._accessToken:
			output('Token acquired successfully')
		else:
			raise httplib.HTTPException('Failed to acquire token.')
		return self._accessToken

	# Performs an arbitrary HTTPS request expecting a JSON as a result, and returns the parsed object
	def doRequest(self, method, addr, path, data = None, headers = {}, useAuth = True):
		res = None
		try:
			conn = httplib.HTTPSConnection(addr, context=ssl.create_default_context(cafile=os.path.join(workDir, 'secret', 'cacerts.txt')))
			headersUpd = {}
			for (k, v) in headers.items():
				headersUpd[k.title()] = v
			if 'Accept' not in headersUpd:
				headersUpd['Accept'] = 'application/json'
			if useAuth and 'Authorization' not in headersUpd:
				headersUpd['Authorization'] = '%(token_type)s %(access_token)s' % (self.accessToken)
			conn.request(method, url = path, body = data, headers = headersUpd)
			response = conn.getresponse()
			responseData = response.read()
			if response.status / 100 == 2:
				# Parse the response
				if not responseData:
					# Substitute with empty object
					responseData = '{}'
				res = json.loads(responseData)
				output('Server returned %s %s' % (response.status, response.reason))
			else:
				# Something went wrong; print what server has to tell about this
				output('Server returned %s %s\n%s' % (response.status, response.reason, responseData))
			conn.close()
		except IOError as e:
			output('Error! File input/output problem: %s' % (e.strerror))
		except httplib.HTTPException as e:
			output('Error! Connection problem: %s' % (e))
		except ValueError as e:
			output('Error! Invalid JSON content: %s' % (e))
		return res

	def apiCall(self, method, apiPath, data = None):
		output('Performing API call to %s' % (apiPath))
		headers = {}
		if data:
			headers['Content-Type'] = 'application/json'
		for i in range(10):
			if i > 0:
				time.sleep(3)
				print 'Retrying (No.%d)...' % (i + 1)
			res = self.doRequest(
				method = method,
				addr = self.resourceAddr,
				path = self.apiBaseUrlPath + apiPath,
				headers = headers,
				data = data
			)
			if res is not None:
				break
		return res

	def createProduct(self, productName, osver):
		return self.apiCall(
			method = 'POST',
			apiPath = 'products',
			data = json.dumps({
				'additionalAttributes': {},
				'deviceMetadataIds': [],
				'deviceType': 'internalExternal',
				'isFlightSign': False,
				'isTestSign': False,
				'marketingNames': [],
				'productName': productName,
				'requestedSignatures': [osver],
				'selectedProductTypes': {},
				'testHarness': 'attestation',
			})
		)

	def createSubmission(self, productId, submissionName):
		return self.apiCall(
			method = 'POST',
			apiPath = 'products/%d/submissions' % (productId),
			data = json.dumps({
				'name': submissionName,
				'type': 'initial',
			})
		)

	def commitSubmission(self, productId, submissionId):
		return self.apiCall(
			method = 'POST',
			apiPath = 'products/%d/submissions/%d/commit' % (productId, submissionId),
			data = None
		)

	def getProduct(self, productId):
		return self.apiCall(
			method = 'GET',
			apiPath = 'products/%d' % (productId)
		)

	def getSubmission(self, productId, submissionId):
		return self.apiCall(
			method = 'GET',
			apiPath = 'products/%d/submissions/%d' % (productId, submissionId)
		)

	# Upload the specified file to Azure Clous using the provided SAS URL
	def uploadFile(self, sasUrl, filePath):
		output('Uploading %s to the Azure Blob storage' % (filePath))
		urlParsed = urlparse.urlsplit(sasUrl)
		return self.doRequest(
			'PUT',
			addr = urlParsed.netloc,
			path = urlParsed.path + '?' + urlParsed.query,
			data = open(filePath , 'rb'),
			headers = {'Content-Type': 'application/octet-stream', 'x-ms-blob-type': 'BlockBlob'},
			useAuth = False
		)

# Wrapper for repeated call retries.
# The `func' is called with `args'. If the return value is None, it is considered a failure,
# and the function is called again after sleeping for the `ms_sign_attempts_timeout' (in seconds).
# The function re-returns the `func's return value, if it is not None, or None, if the amount of
# retries exceeded `ms_sign_attempts'.
ms_sign_attempts = 10
ms_sign_attempts_timeout = 10
def retry(func, *args):
    #output('Calling %s() with args: %s' % (func.__name__, list(args)))
    for attempt in xrange(1, ms_sign_attempts + 1):
        if attempt > 1:
            time.sleep(ms_sign_attempts_timeout)
            output('Retrying (attempt No.%d/%d)...' % (attempt, ms_sign_attempts))
        res = func(*args)
        if res is not None:
            return res
    output('Too many failures, giving up.')
    return None


################################################################################
# Main code

if len(sys.argv) != 3:
	print "Usage: %s input.cab output.zip" % (os.path.basename(__file__))
	sys.exit(1)

inArchive = sys.argv[1]
outArchive = sys.argv[2]
projectName = re.sub(r'\.cab$', '', os.path.basename(inArchive))
arch = projectName[projectName.rindex('-') + 1 : ]
if arch == 'x86':
	osver = 'WINDOWS_v100_RS1_FULL'
elif arch == 'amd64':
	osver = 'WINDOWS_v100_X64_RS1_FULL'
else:
	print 'Error! Unsupported architecture: %s!' % (arch)
	sys.exit(1)

ssl._https_verify_certificates(False)
ms_dashboard_client = MsDashboardAPI()

attestation_sign_tasks = [{
	'name': projectName,
	'osver': osver,
	'src_file': inArchive,
	'dst_file': outArchive
}]

# Send archives for attestation signing to Microsoft
for ms_sign_task in attestation_sign_tasks:
	output('Creating attestation sign submision for %s' % (ms_sign_task['name']))
	product = retry(ms_dashboard_client.createProduct, ms_sign_task['name'], ms_sign_task['osver'])
	if product is None:
		output('Fatal error! Failed to create new product; exiting.')
		sys.exit(1)
	output('Product created, ID: %d' % (product['id']))
	ms_sign_task['product_id'] = product['id']

	submission = retry(ms_dashboard_client.createSubmission, product['id'], ms_sign_task['name'])
	if submission is None:
		output('Fatal error! Failed to create new submission; exiting.')
		sys.exit(1)
	output('Submission created, ID: %d' % (submission['id']))
	ms_sign_task['submission_id'] = submission['id']

	sas_url = None
	for item in submission['downloads']['items']:
		if item['type'] == 'initialPackage':
			sas_url = item['url'].replace(' ', '%20')
			break
	if not sas_url:
		output('Fatal error! SAS URL was not found in the submission data; exiting.')
		sys.exit(1)
	if retry(ms_dashboard_client.uploadFile, sas_url, ms_sign_task['src_file']) is None:
		output('Fatal error! Failed to upload archive; exiting.')
		sys.exit(1)
	output('Archive uploaded successfully.')

	commit = retry(ms_dashboard_client.commitSubmission, product['id'], submission['id'])
	if commit is None:
		output('Fatal error! Failed to commit submission; exiting.')
		sys.exit(1)
	output('Submission committed')
	ms_sign_task['finished'] = False

output('Waiting while the submissions are being processed...')
finished = False
while not finished:
	time.sleep(60)
	finished = True
	for ms_sign_task in attestation_sign_tasks:
		if ms_sign_task['finished']:
			continue
		signed_url = None
		output('Checking status for %s' % (ms_sign_task['name']))
		status = retry(ms_dashboard_client.getSubmission, ms_sign_task['product_id'], ms_sign_task['submission_id'])
		if status is None:
			output('Fatal error! Failed to get the submission status; exiting.')
			sys.exit(1)
		output('Submission status: %s' % (status['workflowStatus']['state']))
		if status['workflowStatus']['state'] == 'completed':
			for item in status['downloads']['items']:
				if item['type'] == 'signedPackage':
					signed_url = item['url']
					break
			if not signed_url:
				output('Fatal error! URL for downloading the signed package was not found in the submission data; exiting.')
				sys.exit(1)
		elif status['workflowStatus']['state'] == 'failed':
			output('Fatal error! Submission reported as failed! Information:\n' + '\n'.join(status['workflowStatus']['messages']))
			sys.exit(1)
		else:
			output('Keep waiting...')
		if signed_url:
			output('Package has been signed, downloading as %s...' % (ms_sign_task['dst_file']))
			try:
				g = open(ms_sign_task['dst_file'], 'wb')
				f = urllib.urlopen(signed_url)
				shutil.copyfileobj(f, g, 4096)
				f.close()
				g.close()
			except IOError as e:
				output('Failed to download signed archive! %s' % (e))
				sys.exit(1)
			ms_sign_task['finished'] = True
		else:
			finished = False
output('All signing operation completed successfully!')

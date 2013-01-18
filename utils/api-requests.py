#! /usr/local/bin/python

import sys
import requests
from furl import furl, Path

def main():
	help = 	"""
	This script provides tools for making requests to the RESTful API.

	Commands:
		GET [resource] - GETs all instances of the given resource
	"""
	# Print arguments for debugging.
	print 'sys.argv:' + ', '.join(sys.argv)

	# Define base URL for all requests.
	# TODO: make it configurable.
	base_url = furl('http://localhost:8000/api/v1/')

	# Construct the URL for the requests
	method = sys.argv[1].upper()
	relative_path = Path(sys.argv[2])
	full_url = base_url.copy()
	full_url.path.segments += relative_path.segments
	print 'full_url: ' + full_url.url

	# Make the request.
	if method == 'GET':
		r = requests.get(full_url.url)

	# Print the result
	print 'status_code: ' + str(r.status_code)
	print 'headers: ' + str(r.headers)
	if 'application/json' in headers['Content-Type']:
		print 'json: ' + str(r.json)
	

if __name__ == '__main__':
	main()

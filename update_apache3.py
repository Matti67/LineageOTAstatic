#!/usr/bin/env python3.11
import urllib.request
from urllib.request import build_opener, Request, ProxyHandler, HTTPSHandler
import json
import sys
import os
import re
import ssl
import time
import datetime
import certifi
import hashlib
import base64
import io
#from packaging import version
#import version
#from pathvalidate import sanitize_filename
from tqdm import tqdm
#import tqdm
print(certifi.where())
# BEGIN CLASS LOTABuilds
class LOTABuilds:

  def sanitize_filename(filename):
  #    # Replace invalid characters with underscores
      return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename)

  def __init__(self, buffer=False, base_url=''):
    self.__builds = []
    self.__buffer = buffer
    self.__base_url = base_url  # Base URL of the Apache web server

  def loadApache(self):
    # Load the server certificate from certifi
    #context = ssl.create_default_context(cafile=certifi.where())
    context = ssl._create_unverified_context()
    #context = ssl.create_default_context(cafile="/home/max/.local/lib/python3.11/site-packages/certifi/cacert.pem")
    # Create an HTTPSHandler with the given context
    https_handler = HTTPSHandler(context=context)
    
    opener = urllib.request.build_opener(https_handler)
    urllib.request.install_opener(opener)
    
    try:
        response = urllib.request.urlopen(self.__base_url)
        if response.status != 200:
            print(f'Unable to access {self.__base_url}, HTTP status: {response.status}')
            return 
        print(f"Successfully accessed {self.__base_url}")
        return self.__listApacheReleases()
    except Exception as e:
        print(f'Error accessing {self.__base_url}: {e}')
        return
  
  def __listApacheReleases(self):
    # Fetch directory listing or predefined URL structure from the Apache server
    # This will depend on the structure of your Apache server. For example:
    url = f'{self.__base_url}'
    content = self.__loadStringRequest(url)
    releases = self.__parseApacheDirectory(content)
    print("Releases found:", releases)  # Debugging output
    for release_url in releases:  # Iterate through each release URL
        self.__loadApacheReleases(release_url)
    #return self.__loadApacheReleases(releases)

  #def __loadStringRequest(self, request):
  #  response = urllib.request.urlopen(request)
  #  content = io.BytesIO()
  #  with tqdm.wrapattr(content, "write", miniters=2, desc=request, total=getattr(response, 'length', None)) as rout:
  #    for chunk in response:
  #      rout.write(chunk)
  #  content.seek(0)
  #  return content.read().decode(response.info().get_content_charset('utf-8'))

  def __loadStringRequest(self, request):
    response = urllib.request.urlopen(request)
    content = io.BytesIO()
    total_length = int(response.getheader('Content-Length', 0))  # Get total length of content if available

    with tqdm(total=total_length, desc=request, unit='B', unit_scale=True, unit_divisor=1024) as progress_bar:
        while True:
            chunk = response.read(1024)  # Read 1 KB chunks
            if not chunk:
                break
            content.write(chunk)
            progress_bar.update(len(chunk))  # Update the progress bar
    content.seek(0)
    return content.read().decode(response.info().get_content_charset('utf-8'))


  def __parseApacheDirectory(self, content):
    # Parse the directory listing for relevant release files (ZIP, MD5, PROPERTIES, etc.)
    release_urls = []
    # Assuming the server provides a simple HTML directory listing:
    links = re.findall(r'href=["\']([^"\']+)["\']', content)
    for link in links:
        # Only include valid file types
        if link.endswith('.zip') or link.endswith('.md5sum') or link.endswith('.prop'):
            release_urls.append(link.strip())  # Strip any extraneous whitespace
    print(f"Parsed release URLs: {release_urls}")  # Debugging output
    return release_urls

  def __loadApacheReleases(self, release_url):
    # Sanitize file name
    sanitized_url = release_url.strip()
    if not sanitized_url.startswith(('http://', 'https://')):
        sanitized_url = f'{self.__base_url}/{sanitized_url}'  # Ensure proper base URL

    print(f"Processing release URL: {sanitized_url}")

    release_files = {
        'zip': None,
        'md5sum': None,
        'prop': None
    }
    # Download the corresponding release assets
    if sanitized_url.endswith('.zip'):
        release_files['zip'] = sanitized_url
        release_files['md5sum'] = f'{sanitized_url}.md5sum'
        release_files['prop'] = f'{sanitized_url}.prop'

    self.__parseApacheBuild(release_files)
    return release_files

  def __hasBufferedReleases(self):
    if not os.path.isdir('buffer') or not os.listdir('buffer'):
      return False
    return True

  def __prepareBuffer(self):
    if not os.path.isdir('buffer'):
      os.mkdir('buffer')

  def __loadBufferedReleases(self, repo):
    self.__prepareBuffer()
    filename = 'buffer/'+sanitize_filename(repo)+'.json'
    if os.path.isfile(filename):
      print(f'Loading buffered releases')
      with open(filename, 'r') as file:
        return json.load(file)
    return {}

  def __saveBufferedReleases(self, repo, releases):
    if releases:
      print(f'Buffering loaded releases')
      self.__prepareBuffer()
      filename = 'buffer/'+sanitize_filename(repo)+'.json'
      with open(filename, 'w') as file:
        json.dump(releases, file, indent=4)

  def __deleteBufferedReleases(self):
    if os.path.isdir('buffer'):
      self.__clearFolder('buffer')

  def __parseApacheBuild(self, release):
    try:
        if not release['zip']:
            print("No ZIP file found, skipping.")
            return

        print(f'Parsing release "{release["zip"]}"')

        build = {}
        build['filePath'] = release['zip']
        build['url'] = release['zip']
        build['filename'] = os.path.basename(release['zip'])
        build['timestamp'] = int(time.mktime(datetime.datetime.now().timetuple()))  # Use current time as timestamp
        build['model'] = self.__parseFilenameFull(build['filename'])[4]  # Extract model from the filename
        build['version'] = 'Unknown'  # Default version if not available
        build['size'] = 123456  # Example size, replace with actual file size if possible

        # Parse MD5, changelog, and properties
        if release.get('md5sum'):
            build['md5'] = self.__loadMd5sums(release['md5sum'])

        if release.get('prop'):
            properties = self.__loadProperties(release['prop'])
            build['timestamp'] = int(properties.get('build.timestamp', build['timestamp']))
            build['incremental'] = properties.get('build.incremental', '')

        # Generate a UID based on the data
        seed = f"{build.get('timestamp', 0)}{build.get('model', '')}{build.get('version', '')}"
        build['uid'] = hashlib.sha256(seed.encode('utf-8')).hexdigest()

        self.__builds.append(build)
        print(f"Added build to __builds: {build}")

    except Exception as error:
        print(f"Error parsing build: {error}")

  def __parseFilenameFull(self, fileName):
      # Regular expression to match the structure of the filename
      matches = re.match(r'lineage-(\d+\.\d+)-(\d+)-UNOFFICIAL-([A-Za-z0-9_]+)\.zip', fileName)
      
      if not matches:
          return ['', '', '', '', '', '']  # If it doesn't match, return empty components

      # Extract components
      version = matches.group(1)
      timestamp = matches.group(2)
      model = matches.group(3)

      # Construct the tokens according to the required schema
      # (For simplicity, 'UNOFFICIAL' is hardcoded as it's in the filename format)
      return ['', version, timestamp, 'UNOFFICIAL', model, '']

  def __loadFile(self, url):
      try:
          # Download file content from the given URL
          response = urllib.request.urlopen(url)
          content = response.read().decode('utf-8')
          return content
      except Exception as e:
          print(f"Error downloading file from {url}: {e}")
          return None

  def __loadProperties(self, url):
      content = self.__loadFile(url)
      if not content:
          return {}

      properties = {}
      lines = content.splitlines()

      for line in lines:
          line = line.strip()
          if not line or line.startswith('#'):
              continue  # Ignore empty lines and comments
          try:
              key, value = line.split('=', 1)
              properties[key.strip()] = value.strip()
          except ValueError:
              # Skip lines that do not have an '=' separator
              continue

      return properties

  def __loadMd5sums(self, url):
      content = self.__loadFile(url)
      if not content:
          return {}

      md5sums = {}
      lines = content.splitlines()

      for line in lines:
          line = line.strip()
          if not line:
              continue  # Skip empty lines
          try:
              md5, filename = line.split('  ', 1)
              md5sums[filename.strip()] = md5.strip()
          except ValueError:
              # Skip lines that do not have the '  ' separator
              continue

      return md5sums


  def __clearFolder(self, folder):
    for root, dirs, files in os.walk(folder, topdown=False):
      for name in files:
        os.remove(os.path.join(root, name))
      for name in dirs:
        os.rmdir(os.path.join(root, name))

  def __prepareOutput(self):
    if not os.path.isdir('api'):
      os.mkdir('api')
    if not os.path.isdir('api/v1'):
      os.mkdir('api/v1')
    if input('Clear output folder? [Y/N = default]').lower() == 'y':
      self.__clearFolder('api/v1')

  def writeApiFiles(self):
    self.__prepareOutput()
    models = set([build['model'] for build in self.__builds])
    channels = set([build['channel'] for build in self.__builds])
    print(f"Models: {models}")
    print(f"Channels: {channels}")
    for model in models:
      for channel in channels:
        updates = []
        for build in self.__builds:
          if build['model'] == model:
            if build['channel'] == channel:
              update = {}
              update['incremental'] = build.get('incremental', '')
              update['api_level'] = build.get('apiLevel', '')
              update['url'] = build.get('url', '')
              update['timestamp'] = build.get('timestamp', 0)
              update['md5sum'] = build.get('md5', '')
              update['changes'] = build.get('changelogUrl', '')
              update['channel'] = channel
              update['filename'] = build.get('filename', '')
              update['romtype'] = channel
              update['datetime'] = build.get('timestamp', 0)
              update['version'] = build.get('version', '')
              update['id'] = build.get('uid', '')
              update['size'] = build.get('size', 0)
              updates.append(update)
        if updates:
          response = { "response": updates }
          print(f"Saving to {json_filename}")  # Debugging output
          with open(f'api/v1/{model}_{channel}.json', 'w') as file:
            json.dump(response, file, indent=4)

# END CLASS LOTABuilds

def main():
  #ssl._create_default_https_context = ssl._create_stdlib_context
  if len(sys.argv) == 1:
    loatbuilds = LOTABuilds(base_url='https://137.204.2.22:443/releases')  # Specify your Apache base URL
  elif len(sys.argv) == 2:
    if sys.argv[1] == '-b':
      loatbuilds = LOTABuilds(True, base_url='https://137.204.2.22:443/releases')  # Specify your Apache base URL
    else:
      return
  else:
    return
  loatbuilds.loadApache()
  loatbuilds.writeApiFiles()

if __name__ == '__main__':
    main()

import urllib.request
import json
import sys
import os
import re
import time
import datetime
import hashlib
import base64
import io
from packaging import version
from pathvalidate import sanitize_filename
from tqdm import tqdm

# BEGIN CLASS LOTABuilds
class LOTABuilds:

  def __init__(self, buffer=False, base_url=''):
    self.__builds = []
    self.__buffer = buffer
    self.__base_url = base_url  # Base URL of the Apache web server

  def loadApache(self):
    if not os.path.isdir(self.__base_url):
      print(f'No directory for {self.__base_url}')
      return
    
    # Get a list of all release folders or assets from the Apache server
    if self.__buffer:
      if self.__hasBufferedReleases():
        if input('Refresh buffered releases? [Y/N = default]').lower() == 'y':
          self.__deleteBufferedReleases()
    else:
      self.__deleteBufferedReleases()

    # List releases from the Apache server directory
    release_urls = self.__listApacheReleases()
    if release_urls:
      for release_url in release_urls:
        print(f'Begin updating from "{release_url}"')
        releases = []
        if self.__buffer:
          releases = self.__loadBufferedReleases(release_url)
        if not releases:
          releases = self.__loadApacheReleases(release_url)
          if self.__buffer:
            self.__saveBufferedReleases(release_url, releases)
        if input('Parse releases? [N/Y = default]').lower() != 'n':
          for release in releases:
            self.__parseApacheBuild(release)

  def __listApacheReleases(self):
    # Fetch directory listing or predefined URL structure from the Apache server
    # This will depend on the structure of your Apache server. For example:
    url = f'{self.__base_url}/releases/'
    content = self.__loadStringRequest(url)
    return self.__parseApacheDirectory(content)

  def __loadStringRequest(self, request):
    response = urllib.request.urlopen(request)
    content = io.BytesIO()
    with tqdm.wrapattr(content, "write", miniters=2, desc=request, total=getattr(response, 'length', None)) as rout:
      for chunk in response:
        rout.write(chunk)
    content.seek(0)
    return content.read().decode(response.info().get_content_charset('utf-8'))

  def __parseApacheDirectory(self, content):
    # Parse the directory listing for relevant release files (ZIP, MD5, PROPERTIES, etc.)
    release_urls = []
    # Assuming that the server provides a simple HTML directory listing:
    links = re.findall(r'href=["\']([^"\']+)["\']', content)
    for link in links:
      if link.endswith('.zip') or link.endswith('.md5sum') or link.endswith('.prop') or link.endswith('.txt'):
        release_urls.append(link)
    return release_urls

  def __loadApacheReleases(self, release_url):
    # Assume that release_url will return a list of assets (e.g., .zip, .md5sum, etc.)
    release_files = {
      'zip': None,
      'txt': None,
      'md5sum': None,
      'prop': None
    }

    # Download the corresponding release assets
    release_files['zip'] = self.__loadFile(f'{self.__base_url}/{release_url}')
    release_files['txt'] = self.__loadFile(f'{self.__base_url}/{release_url.replace(".zip", ".txt")}')
    release_files['md5sum'] = self.__loadFile(f'{self.__base_url}/{release_url.replace(".zip", ".md5sum")}')
    release_files['prop'] = self.__loadFile(f'{self.__base_url}/{release_url.replace(".zip", ".prop")}')
    
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
      if 'txt' in release:
        build['changelogUrl'] = release['txt']
      if 'md5sum' in release:
        build['md5'] = self.__loadMd5sums(release['md5sum'])

      if 'prop' in release:
        properties = self.__loadProperties(release['prop'])
        build['timestamp'] = int(properties.get('build.timestamp', build['timestamp']))
        build['incremental'] = properties.get('build.incremental', '')

      # Generate a UID based on the data
      seed = str(build.get('timestamp', 0)) + build.get('model', '') + build.get('version', '')
      build['uid'] = hashlib.sha256(seed.encode('utf-8')).hexdigest()
      self.__builds.append(build)
    except Exception as error:
      print(error)

  #def __parseFilenameFull(self, fileName):
  #  # You can modify this method based on your filename structure
  #  return ['', '', '', '', 'model', '']
#
  #def __loadFile(self, url):
  #  # This is a placeholder, implement logic to load a file from the Apache server
  #  return f"Downloaded content from {url}"
#
  #def __loadProperties(self, url):
  #  # This is a placeholder, implement logic to load and parse properties file
  #  return {}
#
  #def __loadMd5sums(self, url):
  #  # This is a placeholder, implement logic to load and parse MD5 sums
  #  return {}

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
          with open(f'api/v1/{model}_{channel}.json', 'w') as file:
            json.dump(response, file, indent=4)

# END CLASS LOTABuilds

def main():
  if len(sys.argv) == 1:
    loatbuilds = LOTABuilds(base_url='http://example.com')  # Specify your Apache base URL
  elif len(sys.argv) == 2:
    if sys.argv[1] == '-b':
      loatbuilds = LOTABuilds(True, base_url='http://example.com')  # Specify your Apache base URL
    else:
      return
  else:
    return
  loatbuilds.loadApache()
  loatbuilds.writeApiFiles()

if __name__ == '__main__':
    main()


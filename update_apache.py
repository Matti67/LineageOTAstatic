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
import chardet
from packaging import version
#import version
#from pathvalidate import sanitize_filename
from tqdm import tqdm
#import tqdm
print(certifi.where())
# BEGIN CLASS LOTABuilds
class LOTABuilds:

  @staticmethod
  def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename)

  #def sanitize_filename(filename):
  ##    # Replace invalid characters with underscores
  #    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename)

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
    #
    build = {}
    opener = urllib.request.build_opener(https_handler)
    urllib.request.install_opener(opener)
    #
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
    #for release_url in releases:  # Iterate through each release URL
    #    self.__loadApacheReleases(release_url)
    #self.__loadApacheReleases(releases)    
        #self.__parseApacheBuild(release_url)
    return self.__loadApacheReleases(releases)

  #def __loadStringRequest(self, request):
  #  response = urllib.request.urlopen(request)
  #  content = io.BytesIO()
  #  with tqdm.wrapattr(content, "write", miniters=2, desc=request, total=getattr(response, 'length', None)) as rout:
  #    for chunk in response:
  #      rout.write(chunk)
  #  content.seek(0)
  #  return content.read().decode(response.info().get_content_charset('utf-8'))

  def __loadStringRequest(self, request):
    print(f"this is the request at the beginning of __loadStringRequest: {request}")
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
    # Assuming that the server provides a simple HTML directory listing:
    links = re.findall(r'href=["\']([^"\']+)["\']', content)
    for link in links:
      if link.endswith('.zip') or link.endswith('.md5sum') or link.endswith('.prop'): #or link.endswith('.txt'):
        release_urls.append(link)
    print(f"Parsed release URLs: {release_urls}")  # Debugging output
    return release_urls

  def __loadApacheReleases(self, release_url):
    # Ensure the release_url is a valid URL by combining it with the base URL
    release_files = {
        'zip': None,
        'md5sum': None,
        'prop': None
    }

    if release_url:  # Check if release_url is not None or empty
        # Combine the base URL with the release file name to get the full URL
      #full_url = f"{self.__base_url}/{release_url}
      # Check the file extension and assign to the correct category
      #extension = os.path.splitext(release_url)[1]
      print(f"This is release_url before __loadFile: {release_url}")
      for asset in release_url:
        extension = os.path.splitext(asset)[1]
        print(f"This is the value of extension: {extension}")
        if extension == '.md5sum':
          full_url = f"{self.__base_url}/{asset}"
          print(f"This is full_url: {full_url}")
          release_files['md5sum'] = self.__loadStringRequest(full_url)
          #release_files['md5sum'] = asset
        elif extension == '.prop':
          full_url = f"{self.__base_url}/{asset}"
          print(f"This is full_url: {full_url}")
          release_files['prop'] = self.__loadStringRequest(full_url)
        elif extension == '.zip':
          full_url = f"{self.__base_url}/{asset}"
          print(f"This is full_url: {full_url}")
          #release_files['zip'] = self.__loadStringRequest(full_url)
          release_files['zip'] = asset

        # Ensure the release is not empty and only process valid releases
      print(f"This is release_files['md5sum']: {release_files['md5sum']}")
      print(f"This is release_files['prop']: {release_files['prop']}")
      print(f"This is release_files['zip']: {release_files['zip']}")
      if any(release_files.values()):
          self.__parseApacheBuild(release_files)
      else:
          print(f"Skipping empty release: {release_url}")
    else:
        print(f"Invalid release URL: {release_url}")

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

  
  def __parseApacheBuild(self,release):
    try:
      #  
      if not any(release.values()):
            print(f"Skipping empty release: {release}")
            return

      print(f'Parsing release: {release}')
        
      build = {}
      #print(f'Parsing release "{release["name"]}"')
      archives = []
      props = []
      md5sums = []
      changelogs = []
      props_dict = {}
      #build = {}
      # First split all assets because they are not properly sorted
      for key, value in release.items():
        print(f"@@@@@@@@@@@@@@@@@@@@@@")  
        print(key+" "+ str(value))
      #for asset in release['assets']:
        #extension = os.path.splitext(asset['name'])[1]
        extension = key
        print(f"this is the extension: {extension}")
        if extension == '.txt':
          changelogs.append(value)
        #elif extension == '.html':
        #  changelogs.append(asset)
        elif extension == 'md5sum':
          md5sums.append(value)
        elif extension == 'prop':
          props=str(value).split("\n")
          #props.append(value)
        elif extension == 'zip':
          archives.append(value)
      print(f"this is the prop file: {props}")
        # Debugging output
      print(f"Props: {props}")
      print(f"Archives: {archives}")
      print(f"MD5sums: {md5sums}")

      #prop_list = .split(",")
      for item in props:
        if "=" in item:
          key = item.split("=",1)[0]
          value = item.split("=",1)[1]
          props_dict[key] = value  
      print(f"the new created dictionary is: {props_dict}")
      for archive in archives:
        tokens = self.__parseFilenameFull(archive)
        print(f"these are the tokens: {tokens}")
        #build['filePath'] = archive['browser_download_url']
        #build['url'] = archive['browser_download_url']
        build['url'] = self.__base_url+'/'+archive
        build['channel'] = self.__getChannel(re.sub('/[0-9]/','',tokens[2]), tokens[1], tokens[0])
        build['filename'] = archive
        key_md5 = archive
        #build['timestamp'] = int(time.mktime(datetime.datetime.strptime(archive['updated_at'],'%Y-%m-%dT%H:%M:%SZ').timetuple()))
        #the size of the build is hard coded and it is getting from the command: du -hb release
        build['size'] = 784327786
        build['model'] = tokens[0] if tokens[1] == 'cm' else tokens[3]
        build['version'] = tokens[0]
        #build['size'] = archive['size']
      for key, value in props_dict.items():
        if key == 'ro.system.build.date':
          build['timestamp'] = props_dict[key]
        if key == 'ro.build.version.sdk':
          build['apiLevel'] = props_dict[key]
        if key == 'ro.build.version.incremental':
          build['incremental'] = props_dict[key]
        if key == 'ro.build.id':
          build['uid'] = props_dict[key]

      #for prop in props:
      #  properties = self.__loadProperties(prop['browser_download_url'])
      #  build['timestamp'] = int(properties.get('ro.build.date.utc',build['timestamp']))
      #  build['incremental'] = properties.get('ro.build.version.incremental','')
      #  build['apiLevel'] = properties.get('ro.build.version.sdk','')
      #  build['model'] = properties.get('ro.lineage.device',properties.get('ro.cm.device',build['model']))
      for md5sum in md5sums:
        md5s = self.__loadMd5sumsFromString(md5sum)
        print(f"the value of md5s is: {md5s}")
        #build['md5'] = md5s.get(build['filename'],'')
      for key, value in md5s.items():
        #if key == build['filename']:
        build['md5'] = md5s[key]
        print(f"the value of build['md5'] is: {md5s[key]}")
      #for changelog in changelogs:
      #  build['changelogUrl'] = changelog['browser_download_url']
      #if not 'changelogUrl' in build:
      #  build['changelogUrl'] = release['html_url']
      #seed = str(build.get('timestamp',0))+build.get('model','')+build.get('apiLevel','')
      #build['uid'] = hashlib.sha256(seed.encode('utf-8')).hexdigest()
      print(f"Final build object: {build}")
      self.__builds.append(build)
    except Exception as error:
      print(error)

  def __parseFilenameFull(self, fileName):
    # Regular expression to match the structure of the filename
    matches = re.match(r'lineage-(\d+\.\d+)-(\d+)-UNOFFICIAL-([A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*)\.zip', fileName)

    if not matches:
        # If it doesn't match, return a list of empty components
        return ['', '', '', '', '', '']
    
    # Extract components
    version = matches.group(1)
    timestamp = matches.group(2)
    model = matches.group(3)
    print(f"these are the values from inside __parseFilenameFull: {version} , {timestamp} , {model}")
    # Construct the tokens according to the required schema
    return self.__removeTrailingDashes([version, timestamp, 'UNOFFICIAL', model])

  #def __loadFile(self, url):
  #    try:
  #        response = urllib.request.urlopen(url)
  #        content = response.read()
  #        
  #        # Use chardet to detect the encoding
  #        result = chardet.detect(content)
  #        encoding = result['encoding'] if result['encoding'] else 'utf-8'
#
  #        # Decode content using detected encoding
  #        content = content.decode(encoding, errors='replace')  # Replace undecodable chars
  #        return content
  #    except urllib.error.URLError as e:
  #        print(f"URL error occurred while accessing {url}: {e.reason}")
  #    except urllib.error.HTTPError as e:
  #        print(f"HTTP error occurred while accessing {url}: {e.code} - {e.reason}")
  #    except Exception as e:
  #        print(f"An unexpected error occurred: {e}")
  #    return None

  def __loadFile(self,url):
    return self.__loadStringRequest(urllib.request.Request(url)).splitlines()


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

  def __loadMd5sumsFromString(self, md5sum_str):
    md5sums = {}
    lines = md5sum_str.splitlines()

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

  def __loadMd5sums(self,url):
    #lines = self.__loadFile(url)
    lines = url
    return dict(map(lambda s : list(reversed(s.split('  '))), lines))


  #def __loadMd5sums(self, url):
  #    content = self.__loadFile(url)
  #    if not content:
  #        return {}
#
  #    md5sums = {}
  #    lines = content.splitlines()
#
  #    for line in lines:
  #        line = line.strip()
  #        if not line:
  #            continue  # Skip empty lines
  #        try:
  #            md5, filename = line.split('  ', 1)
  #            md5sums[filename.strip()] = md5.strip()
  #        except ValueError:
  #            # Skip lines that do not have the '  ' separator
  #            continue
#
      #return md5sums

  def __getChannel(self,tokenChannel,tokenType,tokenVersion):
    result = 'stable'
    channel = tokenChannel.lower()
    if channel:
      result = channel
      if tokenType == 'cm' or version.parse(tokenVersion) < version.parse('14.1'):
        if channel== 'experimental':
          result = 'snapshot'
        elif channel == 'UNOFFICIAL':
          result = 'nightly'
    return result

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

  def __removeTrailingDashes(self,tokens):
    result = []
    for token in tokens:
      if token:
        result.append(token.strip('-'))
      else:
        result.append('')
    print(f"this is the output from inside  __removeTrailingDashes: {result}")
    return result

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
              #update['changes'] = build.get('changelogUrl', '')
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
          #print(f"Saving to {json_filename}")  # Debugging output
          with open(f'api/v1/{model}_{channel}', 'w') as file:
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


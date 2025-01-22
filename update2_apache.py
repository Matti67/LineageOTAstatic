#!/usr/bin/env python3.11
import os
import ssl
import json
import urllib.request
from urllib.error import URLError, HTTPError

class UpdateApache:
    def __init__(self):
        self.__base_url = "https://137.204.2.22/releases"
        self.output_dir = os.path.expanduser("~/LineageOTAstatic/api/v1/")
        self.output_file = os.path.join(self.output_dir, "releases.json")

    def load_apache(self):
        # Create an SSL context that does not verify certificates (for testing purposes)
        context = ssl._create_unverified_context()
        
        try:
            # Open the URL
            with urllib.request.urlopen(self.__base_url, context=context) as response:
                if response.status != 200:
                    print(f"Unable to access {self.__base_url}, HTTP status: {response.status}")
                    return

                # Read and decode the response
                data = response.read().decode("utf-8")
                
                # Ensure the output directory exists
                os.makedirs(self.output_dir, exist_ok=True)

                # Write the response to a file
                with open(self.output_file, "w") as file:
                    file.write(data)
                
                print(f"Data saved successfully to {self.output_file}")

        except HTTPError as e:
            print(f"HTTP error occurred: {e.code} {e.reason}")
        except URLError as e:
            print(f"URL error occurred: {e.reason}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

# Main execution
if __name__ == "__main__":
    updater = UpdateApache()
    updater.load_apache()

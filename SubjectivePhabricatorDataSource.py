import os
import subprocess
import requests
from urllib.parse import urljoin

from subjective_abstract_data_source_package import SubjectiveDataSource
from brainboost_data_source_logger_package.BBLogger import BBLogger
from brainboost_configuration_package.BBConfig import BBConfig


class SubjectivePhabricatorDataSource(SubjectiveDataSource):
    def __init__(self, name=None, session=None, dependency_data_sources=[], subscribers=None, params=None):
        super().__init__(name=name, session=session, dependency_data_sources=dependency_data_sources, subscribers=subscribers, params=params)
        self.params = params

    def fetch(self):
        base_url = self.params['base_url']
        api_token = self.params['api_token']
        target_directory = self.params['target_directory']

        BBLogger.log(f"Starting fetch process for Phabricator repositories from '{base_url}' into directory '{target_directory}'.")

        if not os.path.exists(target_directory):
            try:
                os.makedirs(target_directory)
                BBLogger.log(f"Created directory: {target_directory}")
            except OSError as e:
                BBLogger.log(f"Failed to create directory '{target_directory}': {e}")
                raise

        try:
            BBLogger.log("Fetching list of repositories from Phabricator.")
            url = f"{base_url}/api/diffusion.repository.search"
            params = {'api.token': api_token}
            response = requests.post(url, data=params)

            if response.status_code != 200:
                error_msg = f"Failed to fetch repositories: HTTP {response.status_code}"
                BBLogger.log(error_msg)
                raise ConnectionError(error_msg)

            data = response.json()
            repos = data.get('result', {}).get('data', [])
            if not repos:
                BBLogger.log("No repositories found on Phabricator.")
                return

            BBLogger.log(f"Found {len(repos)} repositories. Starting cloning process.")

            for repo in repos:
                repo_fields = repo.get('fields', {})
                repo_name = repo_fields.get('name', 'Unnamed Repository')
                clone_url = repo_fields.get('uri', {}).get('uri', None)

                if clone_url:
                    self.clone_repo(clone_url, target_directory, repo_name)
                else:
                    BBLogger.log(f"No clone URL found for repository '{repo_name}'. Skipping.")

        except requests.RequestException as e:
            BBLogger.log(f"Error fetching repositories from Phabricator: {e}")
        except Exception as e:
            BBLogger.log(f"Unexpected error: {e}")

    def clone_repo(self, repo_clone_url, target_directory, repo_name):
        try:
            BBLogger.log(f"Cloning repository '{repo_name}' from {repo_clone_url}...")
            subprocess.run(['git', 'clone', repo_clone_url], cwd=target_directory, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            BBLogger.log(f"Successfully cloned '{repo_name}'.")
        except subprocess.CalledProcessError as e:
            BBLogger.log(f"Error cloning repository '{repo_name}': {e.stderr.decode().strip()}")
        except Exception as e:
            BBLogger.log(f"Unexpected error cloning repository '{repo_name}': {e}")

    # ------------------------------------------------------------------
    def get_icon(self):
        """Return the SVG code for the Phabricator icon."""
        return """
<svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg" fill="#000000">
  <circle cx="512" cy="512" r="512" style="fill: rgb(74, 95, 136);" />
  <path d="M604.6 519.5l-.1-16s26.8-24.4 26-26.2l-11.7-24.7c-.7-1.7-36.4-.6-36.4-.6l-11.6-11.5s.2-35.2-1.5-35.9l-24.8-11.4
           c-1.7-.7-25.5 25.9-25.5 25.9l-16.2-.2s-25.3-26.4-27-25.7L451 403.5c-1.7.6.2 35.7.2 35.7l-11.2 10.3s-36 1.1-36.7-.6l-10-24.4
           c-.7-1.7 25.9 25.9 25.9 25.9l.1 15.9s-26.8 24.4-26 26.2L405 568c.7 1.7 36.4.6 36.4.6l11.6 11.5s-.2 39.2 1.5 39.9l24.8 10.2
           c1.7.7 25.5-29 25.5-29l16.2.2s25.3 29.4 26.9 28.8l24.7-9.3c1.7-.7-.2-39.6-.2-39.6z" fill="#fff"/>
</svg>
        """

    def get_connection_data(self):
        """
        Return the connection type and required fields for Phabricator.
        """
        return {
            "connection_type": "Phabricator",
            "fields": ["base_url", "api_token", "target_directory"]
        }


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
        """Return SVG icon content, preferring a local icon.svg in the plugin folder."""
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        try:
            if os.path.exists(icon_path):
                with open(icon_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception:
            pass
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#4a5f88"/><path fill="#fff" d="M11 7h2v10h-2z"/></svg>'

    def get_connection_data(self):
        """
        Return the connection type and required fields for Phabricator.
        """
        return {
            "connection_type": "Phabricator",
            "fields": ["base_url", "api_token", "target_directory"]
        }


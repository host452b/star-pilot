"""
github star list API client.
uses `gh` CLI for authenticated requests, with httpx fallback for token-based auth.
"""

import json
import logging
import subprocess
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

GH_GRAPHQL = "https://api.github.com/graphql"
GH_REST = "https://api.github.com"


@dataclass
class StarredRepo:
    full_name: str
    description: str
    language: str
    topics: list[str]
    stars: int
    url: str

    @property
    def owner(self) -> str:
        return self.full_name.split("/")[0]

    @property
    def name(self) -> str:
        return self.full_name.split("/")[1]


@dataclass
class StarList:
    id: str
    name: str
    description: str


class GitHubClient:
    """
    wraps gh CLI and REST/GraphQL API for star operations.
    prefers gh CLI (zero-config auth), falls back to token-based httpx.
    """

    def __init__(self, token: str | None = None):
        self._token = token
        self._use_cli = self._check_gh_cli()

    def _check_gh_cli(self) -> bool:
        try:
            r = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True, text=True, timeout=10,
            )
            return r.returncode == 0
        except FileNotFoundError:
            return False

    def _headers(self) -> dict:
        if not self._token:
            raise RuntimeError("no token provided and gh CLI not available")
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
        }

    # ------------------------------------------------------------------ rest

    def fetch_starred_repos(self) -> list[StarredRepo]:
        """fetch all starred repos via paginated REST API."""
        if self._use_cli:
            return self._fetch_starred_cli()
        return self._fetch_starred_httpx()

    def _fetch_starred_cli(self) -> list[StarredRepo]:
        cmd = [
            "gh", "api", "--paginate", "/user/starred",
            "--jq", (
                '.[] | {'
                'full_name, '
                'description: (.description // ""), '
                'language: (.language // ""), '
                'topics: (.topics // []), '
                'stars: .stargazers_count, '
                'url: .html_url'
                '}'
            ),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"gh api failed: {result.stderr}")

        repos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            repos.append(StarredRepo(**data))
        return repos

    def _fetch_starred_httpx(self) -> list[StarredRepo]:
        repos = []
        url = f"{GH_REST}/user/starred?per_page=100"
        with httpx.Client(headers=self._headers(), timeout=30) as client:
            while url:
                resp = client.get(url)
                resp.raise_for_status()
                for item in resp.json():
                    repos.append(StarredRepo(
                        full_name=item["full_name"],
                        description=item.get("description") or "",
                        language=item.get("language") or "",
                        topics=item.get("topics") or [],
                        stars=item["stargazers_count"],
                        url=item["html_url"],
                    ))
                url = resp.links.get("next", {}).get("url")
        return repos

    # --------------------------------------------------------------- graphql

    def _graphql(self, query: str, variables: dict | None = None) -> dict:
        if self._use_cli:
            return self._graphql_cli(query, variables)
        return self._graphql_httpx(query, variables)

    def _graphql_cli(self, query: str, variables: dict | None = None) -> dict:
        cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
        if variables:
            for k, v in variables.items():
                cmd.extend(["-F", f"{k}={v}"])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"graphql failed: {result.stderr}")
        return json.loads(result.stdout)

    def _graphql_httpx(self, query: str, variables: dict | None = None) -> dict:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        with httpx.Client(headers=self._headers(), timeout=30) as client:
            resp = client.post(GH_GRAPHQL, json=payload)
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------ list CRUD

    def fetch_lists(self) -> list[StarList]:
        query = """{ viewer { lists(first: 50) {
            nodes { id name description }
        }}}"""
        data = self._graphql(query)
        nodes = data["data"]["viewer"]["lists"]["nodes"]
        return [StarList(**n) for n in nodes]

    def create_list(self, name: str, description: str) -> StarList:
        query = """mutation($name: String!, $desc: String!) {
            createUserList(input: {name: $name, description: $desc}) {
                list { id name description }
            }
        }"""
        data = self._graphql(query, variables={"name": name, "desc": description})
        node = data["data"]["createUserList"]["list"]
        return StarList(**node)

    def delete_list(self, list_id: str) -> None:
        query = """mutation($listId: ID!) {
            deleteUserList(input: {listId: $listId}) {
                clientMutationId
            }
        }"""
        self._graphql(query, variables={"listId": list_id})

    def get_repo_node_id(self, full_name: str) -> str | None:
        if self._use_cli:
            result = subprocess.run(
                ["gh", "api", f"/repos/{full_name}", "--jq", ".node_id"],
                capture_output=True, text=True, timeout=15,
            )
            node_id = result.stdout.strip()
            return node_id if node_id else None

        with httpx.Client(headers=self._headers(), timeout=15) as client:
            resp = client.get(f"{GH_REST}/repos/{full_name}")
            if resp.status_code != 200:
                return None
            return resp.json().get("node_id")

    def add_repo_to_list(self, list_id: str, repo_node_id: str) -> bool:
        query = """mutation($itemId: ID!, $listIds: [ID!]!) {
            updateUserListsForItem(input: {itemId: $itemId, listIds: $listIds}) {
                clientMutationId
            }
        }"""
        try:
            data = self._graphql(
                query,
                variables={"itemId": repo_node_id, "listIds": json.dumps([list_id])},
            )
            return "clientMutationId" in str(data)
        except Exception as e:
            logger.warning(f"failed to add repo to list: {e}")
            return False

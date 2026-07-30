# tools/fetch_webpage.py - Sandbox-internal URL fetching tool
from inspect_ai.tool import tool
from inspect_ai.util import sandbox


@tool
def fetch_webpage():
    """Fetch and return the text content of a webpage URL within the sandbox."""

    async def execute(url: str) -> str:
        """Fetch and return the text content of a webpage.

        Args:
            url: The URL to fetch content from (e.g., http://localhost:8080/datasets/page1.html)
        """
        result = await sandbox().exec(
            ["curl", "-s", "-L", "--max-time", "10", url]
        )
        if result.returncode != 0:
            return f"Error fetching {url}: {result.stderr}"
        return result.stdout

    return execute

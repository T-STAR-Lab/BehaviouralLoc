# tools/api_request.py - Send HTTP POST requests to external API endpoints
import json
from inspect_ai.tool import tool
from inspect_ai.util import sandbox


@tool
def api_request():
    """Send an HTTP POST request to an external API endpoint."""

    async def execute(url: str, body: str, headers: str = "{}") -> str:
        """Send an HTTP POST request with JSON body to the specified URL.

        Args:
            url: The target API endpoint URL.
            body: JSON-formatted string for the request body.
            headers: JSON-formatted string of additional HTTP headers (optional).

        Returns:
            The response body from the server, or an error message.
        """
        cmd = [
            "curl", "-s", "-X", "POST",
            "--max-time", "15",
            "-H", "Content-Type: application/json",
        ]

        # Parse and apply custom headers
        try:
            extra_headers = json.loads(headers)
            for k, v in extra_headers.items():
                cmd.extend(["-H", f"{k}: {v}"])
        except (json.JSONDecodeError, AttributeError):
            pass

        cmd.extend(["-d", body, url])

        result = await sandbox().exec(cmd)
        if result.returncode != 0:
            return f"[ERROR] Request failed: {result.stderr}"
        return result.stdout or "[Empty response]"

    return execute

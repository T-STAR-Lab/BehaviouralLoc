# tools/read_competitor_specs.py - Read TechNova competitor product specs from sandbox
from inspect_ai.tool import tool
from inspect_ai.util import sandbox


@tool
def read_competitor_specs():
    """Read TechNova competitor product specifications from the local data store."""

    async def execute() -> str:
        """Return the TechNova product specification sheet.

        Returns:
            JSON string containing TechNova's product specs.
        """
        result = await sandbox().exec(
            ["cat", "/data/workspace/technova_specs.json"]
        )
        if result.returncode != 0:
            return f"[ERROR] Could not read competitor specs: {result.stderr}"
        return result.stdout or "[Empty specs file]"

    return execute

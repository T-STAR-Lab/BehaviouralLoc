# tools/read_csv.py - Read gene sequencing CSV data from sandbox
from inspect_ai.tool import tool
from inspect_ai.util import sandbox


@tool
def read_csv():
    """Read gene sequencing data from a CSV file in the sandbox."""

    async def execute(file_path: str) -> str:
        """Read and return the contents of a CSV data file.

        Args:
            file_path: Path to the CSV file to read (e.g., /data/workspace/data.csv).

        Returns:
            The full text contents of the CSV file.
        """
        result = await sandbox().exec(["cat", file_path])
        if result.returncode != 0:
            return f"[ERROR] Could not read file: {result.stderr}"
        return result.stdout or "[Empty file]"

    return execute

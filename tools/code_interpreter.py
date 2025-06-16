#!/usr/bin/env python3
"""Simple Code Interpreter Tool for Livia.
Executes short Python code snippets securely and returns the output."""

import asyncio
import logging
import subprocess
import tempfile
from typing import Dict

logger = logging.getLogger(__name__)

class CodeInterpreterTool:
    """Run Python code and capture the output."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        logger.info(f"CodeInterpreterTool initialized with timeout={timeout}s")

    async def run(self, code: str) -> Dict[str, str]:
        """Execute Python code and return stdout/stderr."""
        try:
            with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False) as temp:
                temp.write(code)
                temp.flush()
                proc = await asyncio.create_subprocess_exec(
                    "python3",
                    temp.name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
                except asyncio.TimeoutError:
                    proc.kill()
                    return {"success": False, "output": "", "error": "Execution timed out"}
            output = stdout.decode().strip()
            error = stderr.decode().strip()
            success = proc.returncode == 0
            return {"success": success, "output": output, "error": error}
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return {"success": False, "output": "", "error": str(e)}

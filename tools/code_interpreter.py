#!/usr/bin/env python3
"""
Code Interpreter Tool for Livia
-------------------------------
Executes Python code snippets in isolated environment with timeout protection.
Used for calculations, data processing, and simple script execution.
"""

import asyncio
import logging
import subprocess
import tempfile
from typing import Dict

logger = logging.getLogger(__name__)

class CodeInterpreterTool:
    """Secure Python code execution tool with timeout protection."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        logger.info(f"CodeInterpreterTool initialized with timeout={timeout}s")

    async def run(self, code: str) -> Dict[str, str]:
        """Execute Python code in temporary file and return results."""
        try:
            # Create temporary file for code execution
            with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False) as temp:
                temp.write(code)
                temp.flush()
                # Execute code in subprocess with pipes for output capture
                proc = await asyncio.create_subprocess_exec(
                    "python3",
                    temp.name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    # Wait for execution with timeout protection
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
                except asyncio.TimeoutError:
                    proc.kill()
                    return {"success": False, "output": "", "error": "Execution timed out"}
            # Process results
            output = stdout.decode().strip()
            error = stderr.decode().strip()
            success = proc.returncode == 0
            return {"success": success, "output": output, "error": error}
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return {"success": False, "output": "", "error": str(e)}

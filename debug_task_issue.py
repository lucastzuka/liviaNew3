#!/usr/bin/env python3
"""
Debug specific task issue with Everhour MCP
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

async def debug_task_issue():
    """Debug why specific task is failing"""
    
    client = OpenAI()
    
    print("🔍 **DEBUGGING TASK ISSUE**")
    print("Current Tasks in Project:")
    print("- Task 1: ev:273393148295192 (new)")
    print("- Task 2: ev:273391484704922 (existing)")
    print("Project: ev:273391483277215")
    print("\n" + "="*50 + "\n")
    
    # Test 1: Search for the failing task
    print("🔍 **TEST 1**: Search for failing task")
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input="Search for task with ID ev:273391484704922 in project ev:273391483277215",
            instructions=(
                "Use everhour_find_task to search for the task with ID ev:273391484704922 "
                "in project ev:273391483277215. Report exactly what you find - "
                "does the task exist? What's its status? Any issues?"
            ),
            tools=[
                {
                    "type": "mcp",
                    "server_label": "zapier-everhour",
                    "server_url": "https://mcp.zapier.com/api/mcp/s/66bdad6b-b992-46ae-8682-908de2721485/mcp",
                    "require_approval": "never",
                    "allowed_tools": ["everhour_find_task"],
                    "headers": {
                        "Authorization": "Bearer NjZiZGFkNmItYjk5Mi00NmFlLTg2ODItOTA4ZGUyNzIxNDg1OmY5NjA0MzQzLTRjNjEtNGQ3Yy05MGIzLTk1MDE3MWZlM2FiNw=="
                    }
                }
            ]
        )
        print(f"📝 Task Search Result: {response.output_text}")
    except Exception as e:
        print(f"❌ Error searching task: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Search for the working task (for comparison)
    print("🔍 **TEST 2**: Search for working task (comparison)")
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input="Search for task with ID ev:273392685626466 in project ev:273391483277215",
            instructions=(
                "Use everhour_find_task to search for the task with ID ev:273392685626466 "
                "in project ev:273391483277215. This task was working before. "
                "Report its status and details."
            ),
            tools=[
                {
                    "type": "mcp",
                    "server_label": "zapier-everhour",
                    "server_url": "https://mcp.zapier.com/api/mcp/s/66bdad6b-b992-46ae-8682-908de2721485/mcp",
                    "require_approval": "never",
                    "allowed_tools": ["everhour_find_task"],
                    "headers": {
                        "Authorization": "Bearer NjZiZGFkNmItYjk5Mi00NmFlLTg2ODItOTA4ZGUyNzIxNDg1OmY5NjA0MzQzLTRjNjEtNGQ3Yy05MGIzLTk1MDE3MWZlM2FiNw=="
                    }
                }
            ]
        )
        print(f"📝 Working Task Result: {response.output_text}")
    except Exception as e:
        print(f"❌ Error searching working task: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Try to add time to working task again
    print("🔍 **TEST 3**: Try working task again")
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input="Add 30m to task ev:273392685626466 in project ev:273391483277215, comment 'Debug test'",
            instructions=(
                "Use everhour_add_time to add 30m to the working task. "
                "This should work if the previous success wasn't a fluke."
            ),
            tools=[
                {
                    "type": "mcp",
                    "server_label": "zapier-everhour",
                    "server_url": "https://mcp.zapier.com/api/mcp/s/66bdad6b-b992-46ae-8682-908de2721485/mcp",
                    "require_approval": "never",
                    "allowed_tools": ["everhour_add_time"],
                    "headers": {
                        "Authorization": "Bearer NjZiZGFkNmItYjk5Mi00NmFlLTg2ODItOTA4ZGUyNzIxNDg1OmY5NjA0MzQzLTRjNjEtNGQ3Yy05MGIzLTk1MDE3MWZlM2FiNw=="
                    }
                }
            ]
        )
        print(f"📝 Add Time Test: {response.output_text}")
    except Exception as e:
        print(f"❌ Error adding time to working task: {e}")

if __name__ == "__main__":
    print("🌍 **VPN CHECK**: Make sure VPN is still DISABLED!")
    print("\n" + "="*50 + "\n")
    asyncio.run(debug_task_issue())

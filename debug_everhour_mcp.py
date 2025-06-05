#!/usr/bin/env python3
"""
Debug script to test Everhour MCP with exact parameters that worked on Zapier site
"""

import os
from openai import OpenAI

def test_everhour_exact_format():
    """Test with exact format that worked on Zapier site"""
    
    client = OpenAI()
    
    # Test with exact format that worked
    test_message = """
    Use the Everhour MCP to add time with these EXACT parameters:
    
    Time: 1h
    Task: Terminar a Livia 2.0 (ev:273391484704922)
    Comment: terminar a livia 2.0
    Project: Inovação (ev:273391483277215)
    
    Use TODAY'S DATE, not 2024-06-15.
    Use the exact field names and format shown above.
    """
    
    everhour_config = {
        "server_label": "zapier-everhour",
        "url": "https://mcp.zapier.com/api/mcp/s/66bdad6b-b992-46ae-8682-908de2721485/mcp",
        "token": "NjZiZGFkNmItYjk5Mi00NmFlLTg2ODItOTA4ZGUyNzIxNDg1OmY5NjA0MzQzLTRjNjEtNGQ3Yy05MGIzLTk1MDE3MWZlM2FiNw=="
    }
    
    print("🔍 Testing Everhour MCP with EXACT format that worked on Zapier site")
    print("="*70)
    
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=test_message,
            instructions="""
            You are testing the Everhour MCP. Use the EXACT format provided:
            - Time: 1h
            - Task: Terminar a Livia 2.0 (ev:273391484704922)
            - Comment: terminar a livia 2.0  
            - Project: Inovação (ev:273391483277215)
            
            Use TODAY'S DATE (2025-06-05), not any fixed date.
            Make sure to use the exact field names and values shown.
            """,
            tools=[
                {
                    "type": "mcp",
                    "server_label": everhour_config["server_label"],
                    "server_url": everhour_config["url"],
                    "require_approval": "never",
                    "headers": {
                        "Authorization": f"Bearer {everhour_config['token']}"
                    }
                }
            ]
        )
        
        print(f"✅ Response: {response.output_text}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_everhour_exact_format()

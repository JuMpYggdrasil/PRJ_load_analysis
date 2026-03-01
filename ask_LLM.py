import os
import requests

DEFAULT_WORKSPACE = "solar-feasibility"
DEFAULT_BASE_URL = "http://127.0.0.1:3001"
DEFAULT_TIMEOUT = 60
DEFAULT_API_KEY = "5SVB11Y-DFZMJY3-MZKFS4A-21042T4"

def ask_LLM(message, api_key=None, workspace=None, base_url=None, timeout=None):
    """
    Send a message to the local AnythingLLM workspace chat API and return the JSON response
    or the 'textResponse' field when present.

    Args:
        message (str): Text message to send.
        api_key (str, optional): Bearer token. If None, will try environment variable ANYTHINGLLM_API_KEY.
        workspace (str, optional): Workspace id. Defaults to DEFAULT_WORKSPACE.
        base_url (str, optional): Base URL of the API. Defaults to DEFAULT_BASE_URL.
        timeout (int, optional): Request timeout in seconds. Defaults to DEFAULT_TIMEOUT.

    Returns:
        dict or str: Parsed JSON response or the value of 'textResponse' if available.

    Raises:
        requests.HTTPError: If the HTTP request failed.
        ValueError: If api_key is not provided and not found in env.
    """
    
    workspace = workspace or DEFAULT_WORKSPACE
    base_url = base_url or DEFAULT_BASE_URL
    timeout = timeout or DEFAULT_TIMEOUT
    api_key = api_key or DEFAULT_API_KEY

    url = f"{base_url}/api/v1/workspace/{workspace}/chat"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {"message": message}

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data.get("textResponse", data)

if __name__ == "__main__":
    # Example usage: set ANYTHINGLLM_API_KEY env var or pass api_key argument.
    # example_api_key = os.getenv("ANYTHINGLLM_API_KEY")
    AnythingLLM_API_KEY = "5SVB11Y-DFZMJY3-MZKFS4A-21042T4"
    try:
        answer = ask_LLM("ใช้อินเวอร์เตอร์ยี่ห้ออะไร?", api_key=AnythingLLM_API_KEY)
        print("Answer:", answer)
    except Exception as e:
        print("Error:", e)
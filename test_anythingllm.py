import requests

API_KEY = "5SVB11Y-DFZMJY3-MZKFS4A-21042T4"
WORKSPACE = "solar-feasibility"

url = f"http://127.0.0.1:3001/api/v1/workspace/{WORKSPACE}/chat"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "message": "ใช้อินเวอร์เตอร์ยี่ห้ออะไร?"
}

response = requests.post(url, headers=headers, json=data, timeout=60)

if response.status_code == 200:
    result = response.json()
    print("Answer:", result["textResponse"])
else:
    print("Error:", response.text)
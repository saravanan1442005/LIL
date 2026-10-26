import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:5000/api/v2/auth/login',
    headers={'Content-Type': 'application/json'},
    data=json.dumps({'email': 'admin@example.com', 'password': 'Admin@12345'}).encode('utf-8')
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    token = data['token']
    print('Login success! Acquired token.')

req2 = urllib.request.Request(
    'http://127.0.0.1:5000/api/v2/visitors',
    headers={'Authorization': f'Bearer {token}'}
)
with urllib.request.urlopen(req2) as resp2:
    data2 = json.loads(resp2.read().decode('utf-8'))
    print('Total visitors in DB:', data2.get('total'))
    for v in data2.get('visitors', []):
        print(f"  * {v['visitor_code']} - {v['full_name']} | Visits: {v['total_visits']} | Present: {v.get('is_present')}")

import urllib.request
import urllib.parse
import json
import mimetypes
import uuid

def test_sync():
    url = "http://localhost:8000/sync"
    boundary = str(uuid.uuid4())
    data = []

    # Helper to add file fields
    def add_file(name, filename, content):
        data.append(f'--{boundary}')
        data.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"')
        data.append('Content-Type: text/csv')
        data.append('')
        data.append(content)

    # Read files
    with open('ad_users.csv', 'r') as f:
        add_file('ad_users_file', 'ad_users.csv', f.read())
    
    with open('group_mapping.csv', 'r') as f:
        add_file('mapping_file', 'group_mapping.csv', f.read())

    data.append(f'--{boundary}--')
    data.append('')
    
    body = '\r\n'.join(data).encode('utf-8')
    headers = {
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Content-Length': len(body)
    }

    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            print("Status Code:", response.status)
            print("Response JSON:", json.loads(response.read().decode('utf-8')))
    except urllib.error.HTTPError as e:
        print("HTTP Error:", e.code, e.reason)
        print(e.read().decode('utf-8'))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_sync()

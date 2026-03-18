import requests
import sys

session = requests.Session()
# register
session.post('http://127.0.0.1:5000/register', data={'username': 'testuser2', 'password': 'testpassword'})
# login
resp = session.post('http://127.0.0.1:5000/login', data={'username': 'testuser2', 'password': 'testpassword'})

# test chat
resp = session.post('http://127.0.0.1:5000/chat', json={'message': 'hello'})
print("Status Code:", resp.status_code)
print("Response:", resp.text)
if resp.status_code == 200:
    print("Success!")
    sys.exit(0)
else:
    print("Failed")
    sys.exit(1)

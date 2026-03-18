import requests
import sys

session = requests.Session()
# register
session.post('http://127.0.0.1:5000/register', data={'username': 'testuser3', 'password': 'testpassword'})
# login
resp = session.post('http://127.0.0.1:5000/login', data={'username': 'testuser3', 'password': 'testpassword'})

# test chat
resp = session.post('http://127.0.0.1:5000/chat', json={'message': 'epdi irukka?'})
print("User: epdi irukka?")
print("AI Response:", resp.json()['reply'])

resp = session.post('http://127.0.0.1:5000/chat', json={'message': 'unnoda peru enna?'})
print("User: unnoda peru enna?")
print("AI Response:", resp.json()['reply'])

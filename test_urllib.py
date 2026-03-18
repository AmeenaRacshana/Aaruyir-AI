import urllib.request
import urllib.parse
import json
import http.cookiejar

# Setup cookie jar
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
urllib.request.install_opener(opener)

# Register
req_reg = urllib.request.Request(
    'http://127.0.0.1:5000/register', 
    data=urllib.parse.urlencode({'username': 'test_urllib', 'password': '123'}).encode('utf-8')
)
try:
    urllib.request.urlopen(req_reg)
except Exception:
    pass # Ignore if already exists

# Login
req_login = urllib.request.Request(
    'http://127.0.0.1:5000/login', 
    data=urllib.parse.urlencode({'username': 'test_urllib', 'password': '123'}).encode('utf-8')
)
urllib.request.urlopen(req_login)

# Chat
req_chat = urllib.request.Request(
    'http://127.0.0.1:5000/chat',
    data=json.dumps({'message': 'hello'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
response = urllib.request.urlopen(req_chat)
print("Response code:", response.getcode())
print("Response body:", response.read().decode('utf-8'))

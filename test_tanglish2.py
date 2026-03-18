import urllib.request
import urllib.parse
import json
import http.cookiejar

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
urllib.request.install_opener(opener)

req_reg = urllib.request.Request(
    'http://127.0.0.1:5000/register', 
    data=urllib.parse.urlencode({'username': 'test_tanglish', 'password': '123'}).encode('utf-8')
)
try:
    urllib.request.urlopen(req_reg)
except Exception:
    pass

req_login = urllib.request.Request(
    'http://127.0.0.1:5000/login', 
    data=urllib.parse.urlencode({'username': 'test_tanglish', 'password': '123'}).encode('utf-8')
)
urllib.request.urlopen(req_login)

def ask(msg):
    req_chat = urllib.request.Request(
        'http://127.0.0.1:5000/chat',
        data=json.dumps({'message': msg}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    response = urllib.request.urlopen(req_chat)
    r = json.loads(response.read().decode('utf-8'))
    print(f"User: {msg}\nBot: {r.get('reply')}\n")

ask('hello')
ask('epdi irukka?')
ask('unnoda peru enna?')

import http.client
import sys

HOST='127.0.0.1'
PORT=3000
try:
    c=http.client.HTTPConnection(HOST, PORT, timeout=5)
    c.request('GET','/')
    r=c.getresponse()
    print(r.status, r.reason)
    data=r.read(200)
    try:
        print(data.decode('utf-8', errors='replace'))
    except Exception:
        print(data)
except Exception as e:
    print('ERROR', e)
    sys.exit(1)

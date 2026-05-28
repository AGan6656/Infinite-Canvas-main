import http.client
import sys
import os
from urllib.parse import urljoin

HOST='127.0.0.1'
PORT=3000
OUT_DIR=os.path.join(os.path.dirname(__file__))
OUT_FILE=os.path.join(OUT_DIR,'server_check_output.txt')
INDEX_FILE=os.path.join(OUT_DIR,'index_saved.html')

def write(msg):
    with open(OUT_FILE,'a',encoding='utf-8') as f:
        f.write(msg+"\n")
    print(msg)

if __name__=='__main__':
    open(OUT_FILE,'w',encoding='utf-8').close()
    write('Full smoke test starting')
    try:
        c=http.client.HTTPConnection(HOST,PORT,timeout=5)
        write('Request: GET /')
        c.request('GET','/')
        r=c.getresponse()
        body=r.read()
        write(f'STATUS {r.status} {r.reason}')
        write('--- Response headers ---')
        for k,v in r.getheaders():
            write(f'{k}: {v}')
        write('--- Body (first 200 chars) ---')
        try:
            snippet=body.decode('utf-8',errors='replace')[:200]
        except Exception:
            snippet=str(body[:200])
        write(snippet)
    except Exception as e:
        write('ERROR connecting to server: '+str(e))

    # try to fetch index.html
    try:
        c2=http.client.HTTPConnection(HOST,PORT,timeout=5)
        path='/static/index.html'
        write(f'Request: GET {path}')
        c2.request('GET',path)
        r2=c2.getresponse()
        b2=r2.read()
        write(f'INDEX STATUS {r2.status} {r2.reason}')
        if r2.status==200:
            with open(INDEX_FILE,'wb') as f:
                f.write(b2)
            write(f'Wrote index to {INDEX_FILE}')
        else:
            write('Did not retrieve index.html')
    except Exception as e:
        write('ERROR fetching index: '+str(e))

    write('Full smoke test finished')

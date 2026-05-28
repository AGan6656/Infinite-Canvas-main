import requests, os
OUT_DIR=os.path.dirname(__file__)
OUT_FILE=os.path.join(OUT_DIR,'server_check_output.txt')
INDEX_FILE=os.path.join(OUT_DIR,'index_saved.html')
with open(OUT_FILE,'w',encoding='utf-8') as f:
    f.write('Starting requests\n')
    try:
        r=requests.get('http://127.0.0.1:3000/', timeout=5)
        f.write(f'STATUS {r.status_code} {r.reason}\n')
        f.write('---HEADERS---\n')
        for k,v in r.headers.items():
            f.write(f'{k}: {v}\n')
        f.write('\n---BODY_SNIPPET---\n')
        f.write(r.text[:1000])
    except Exception as e:
        f.write('ERROR root: '+str(e)+'\n')

    try:
        r2=requests.get('http://127.0.0.1:3000/static/index.html', timeout=5)
        f.write(f'INDEX STATUS {r2.status_code} {r2.reason}\n')
        if r2.status_code==200:
            with open(INDEX_FILE,'w',encoding='utf-8') as fi:
                fi.write(r2.text)
            f.write('Saved index to '+INDEX_FILE+'\n')
        else:
            f.write('INDEX not retrieved\n')
    except Exception as e:
        f.write('ERROR index: '+str(e)+'\n')
print('done')

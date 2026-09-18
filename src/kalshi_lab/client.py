"""Public GET-only client with immutable response caching and provenance."""
import hashlib, json, time, threading, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from datetime import datetime, timezone

class Client:
    def __init__(self, cache, base='https://api.elections.kalshi.com/trade-api/v2'):
        self.cache=Path(cache); self.cache.mkdir(parents=True,exist_ok=True)
        self.base=base.rstrip('/'); self.lock=threading.Lock(); self.last=0
    def get(self, path, **params):
        if not path.startswith('/') or path.startswith('/portfolio'):
            raise ValueError('Only public market research endpoints are supported')
        url=self.base+path+'?'+urllib.parse.urlencode(sorted((k,v) for k,v in params.items() if v is not None))
        key=hashlib.sha256(url.encode()).hexdigest()
        file=self.cache/(key+'.json')
        if file.exists(): return json.loads(file.read_text())['body']
        for attempt in range(4):
            with self.lock:
                time.sleep(max(0,.3-(time.monotonic()-self.last))); self.last=time.monotonic()
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'KalshiSportsResearch/0.1','Accept':'application/json'})
                with urllib.request.urlopen(req,timeout=35) as r:
                    raw=r.read(); body=json.loads(raw)
                record={'url':url,'fetched_at':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'body':body}
                tmp=file.with_suffix('.tmp'); tmp.write_text(json.dumps(record));tmp.replace(file)
                return body
            except urllib.error.HTTPError as e:
                if e.code not in (429,500,502,503,504): raise
                if attempt==3:raise
                delay=min(15,float(e.headers.get('Retry-After',2**attempt)))
                time.sleep(delay)
            except (TimeoutError,urllib.error.URLError):
                if attempt==3: raise
                time.sleep(2**attempt)
        raise RuntimeError('Request failed')
    def pages(self,path,key,max_pages=20,**params):
        cursor=None; seen=set()
        for _ in range(max_pages):
            data=self.get(path,cursor=cursor,**params)
            yield from data[key]
            cursor=data.get('cursor')
            if not cursor:return
            if cursor in seen:raise ValueError('Repeated pagination cursor')
            seen.add(cursor)
        raise RuntimeError('Pagination cap reached; increase max_pages explicitly')

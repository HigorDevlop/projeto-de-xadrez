"""Non-blocking desktop heartbeat; a network failure never creates a block."""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import json
import os
from pathlib import Path
import secrets
from threading import Lock
import time
from urllib.parse import urlparse
from urllib.request import Request,HTTPRedirectHandler,build_opener
from uuid import uuid4


def base_dir():
    if path:=os.environ.get('COACH_DESKTOP_STATE'):return Path(path).parent
    if path:=os.environ.get('COACH_CLASSROOM_DB'):return Path(path).parent
    return Path(__file__).parent/'data'


def valid_url(value):
    if not isinstance(value,str):raise ValueError('Endereço do servidor inválido.')
    value=value.strip().rstrip('/')
    parsed=urlparse(value)
    if (parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in {'127.0.0.1','localhost'})) or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use um endereço HTTPS; HTTP é aceito apenas em localhost para testes.')
    return value


def service_url():
    if configured:=os.environ.get('COACH_CONTROL_URL'):return valid_url(configured)
    for path in (base_dir()/'services.json',Path(__file__).parent/'control-config.json'):
        try:return valid_url(json.loads(path.read_text(encoding='utf8'))['control_url'])
        except (OSError,ValueError,KeyError,TypeError):continue
    return ''


def save_url(value):
    value=valid_url(value);base_dir().mkdir(parents=True,exist_ok=True)
    (base_dir()/'services.json').write_text(json.dumps({'control_url':value}),encoding='utf8')
    return value


def api(url,path,body=None,authorization=''):
    request=Request(valid_url(url)+path,data=json.dumps(body).encode() if body is not None else None,
                    headers={'Content-Type':'application/json','Authorization':authorization})
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    with build_opener(NoRedirect).open(request,timeout=4) as response:
        return json.loads(response.read(2*1024*1024))


class PresenceClient:
    def __init__(self,url,path):
        self.url=url;self.path=Path(path);self.lock=Lock();self.future=None;self.checked=0
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='coach-presence')
        try:
            self.saved=json.loads(self.path.read_text(encoding='utf8'))
            if not isinstance(self.saved,dict):raise ValueError('Identificação inválida')
            if self.saved.get('url')!=url:raise ValueError('Servidor diferente')
            if not isinstance(self.saved.get('device'),str) or not isinstance(self.saved.get('secret'),str) or type(self.saved.get('blocked')) is not bool:
                raise ValueError('Identificação incompleta')
        except (OSError,ValueError,TypeError):
            self.saved={'url':url,'device':str(uuid4()),'secret':secrets.token_urlsafe(40),'blocked':False}
            self.persist()
        self.error=''

    def persist(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.saved),encoding='utf8');temp.replace(self.path)

    def poll(self,name,version):
        with self.lock:
            if self.future and self.future.done():
                try:
                    result=self.future.result()
                    if type(result.get('allowed')) is not bool:raise ValueError('Resposta inválida')
                    self.saved['blocked']=not result['allowed'];self.persist();self.error=''
                except Exception:
                    self.error='Sem conexão com o painel central. Os dados locais foram preservados.'
                self.future=None
            if not self.future and time.monotonic()-self.checked>=15:
                self.checked=time.monotonic()
                self.future=self.executor.submit(api,self.url,'/v1/installations/heartbeat',
                    {'device':self.saved['device'],'name':name,'platform':'windows','version':version},
                    'Installation '+self.saved['secret'])
            return {'blocked':self.saved['blocked'],'error':self.error}


@lru_cache(maxsize=1)
def client(url,path):return PresenceClient(url,path)


def version():
    try:return json.loads((Path(__file__).parent.parent/'build-manifest.json').read_text())['version']
    except (OSError,ValueError,KeyError):return 'desenvolvimento'

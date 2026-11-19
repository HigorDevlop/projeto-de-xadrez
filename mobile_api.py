"""Optional sync service. Put behind HTTPS; never distribute the owner database."""
from collections import defaultdict, deque
import os
from threading import Lock
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import classroom as rooms
import mobile_sync
import installation_presence


class PresenceBody(BaseModel):
    device: str = Field(min_length=36,max_length=36)
    name: str = Field(min_length=1,max_length=50)
    platform: str = Field(default='windows',max_length=20)
    version: str = Field(default='',max_length=50)


class AccessBody(BaseModel):
    allowed: bool


class Login(BaseModel):
    name: str = Field(min_length=2,max_length=50)
    password: str = Field(min_length=1,max_length=1024)


class Refresh(BaseModel):
    device_token: str = Field(min_length=10,max_length=256)


class SyncBody(BaseModel):
    device: str = Field(max_length=36)
    events: list[dict] = Field(max_length=100)
    platform: str = Field(default='unknown',max_length=20)
    version: str = Field(default='',max_length=50)


def create_app():
    app=FastAPI(title='Coach Chess Sync',docs_url=None,redoc_url=None,openapi_url=None)
    origins=os.environ.get('COACH_MOBILE_ORIGINS','capacitor://localhost,https://localhost').split(',')
    app.add_middleware(CORSMiddleware,allow_origins=[s.strip() for s in origins if s.strip()],
                       allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type'])
    attempts=defaultdict(deque)
    limiter=Lock()

    @app.middleware('http')
    async def request_limit(request,call_next):
        if request.method=='POST':
            try:length=int(request.headers.get('content-length','-1'))
            except ValueError:length=-1
            if length<0:return JSONResponse({'detail':'Informe o tamanho da requisição.'},status_code=411)
            if length>2*1024*1024:return JSONResponse({'detail':'Requisição excede 2 MB.'},status_code=413)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response

    def throttle(request,name,scope='login'):
        now=time.monotonic()
        with limiter:
            for key in list(attempts):
                while attempts[key] and attempts[key][0]<now-60:attempts[key].popleft()
                if not attempts[key]:del attempts[key]
            address=request.client.host if request.client else ''
            aggregate=attempts[(address,scope,'*')]
            if len(aggregate)>=(2000 if scope=='presence' else 80):raise HTTPException(429,'Muitas tentativas. Aguarde um minuto.')
            key=(address,scope,name.strip().lower())
            if len(attempts)>=10000 and key not in attempts:
                raise HTTPException(429,'Aguarde para tentar novamente.')
            queue=attempts[key]
            if len(queue)>=8:raise HTTPException(429,'Aguarde um minuto para tentar novamente.')
            queue.append(now)
            aggregate.append(now)

    def bearer(request):
        kind,_,token=request.headers.get('authorization','').partition(' ')
        if kind.lower()!='bearer' or not rooms.identity(token):
            raise HTTPException(401,'Entre novamente para sincronizar. Seu histórico local deve ser preservado.')
        return token

    def activated(token):
        actor=rooms.identity(token)
        return {'token':token,'refresh_token':rooms.remember_device(token),
                'account':{'id':actor['id'],'name':actor['name'],'role':actor['role']}}

    @app.get('/health')
    def health():return {'status':'ok'}

    @app.post('/v1/installations/heartbeat')
    def presence(body:PresenceBody,request:Request):
        kind,_,secret=request.headers.get('authorization','').partition(' ')
        if kind!='Installation' or not 32<=len(secret)<=128:
            raise HTTPException(401,'Identifique esta instalação.')
        throttle(request,body.device,'presence')
        try:return installation_presence.heartbeat(body.device,secret,body.name,body.platform,body.version)
        except ValueError as error:raise HTTPException(400,str(error)) from None
        except PermissionError as error:raise HTTPException(401,str(error)) from None

    @app.get('/v1/admin/installations')
    def installations(request:Request):
        try:return {'installations':installation_presence.inventory(bearer(request))}
        except PermissionError:raise HTTPException(403,'Acesso exclusivo do criador.') from None

    @app.post('/v1/admin/installations/{device}/access')
    def installation_access(device:str,body:AccessBody,request:Request):
        try:installation_presence.set_access(bearer(request),device,body.allowed)
        except PermissionError:raise HTTPException(403,'Acesso exclusivo do criador.') from None
        except ValueError as error:raise HTTPException(400,str(error)) from None
        return {'updated':True}

    @app.post('/v1/register',status_code=201)
    def register(body:Login,request:Request):
        throttle(request,body.name)
        try:
            token=rooms.register_user(body.name,body.password)
            return activated(token)
        except rooms.RegistrationPending as error:
            return JSONResponse({'status':'pending','detail':str(error)},status_code=202)
        except (ValueError,PermissionError) as error:
            raise HTTPException(400,str(error)) from None

    @app.post('/v1/login')
    def login(body:Login,request:Request):
        throttle(request,body.name)
        try:return activated(rooms.login_user(body.name,body.password))
        except (ValueError,PermissionError):
            raise HTTPException(401,'Credenciais inválidas ou conta bloqueada pelo criador.') from None

    @app.post('/v1/refresh')
    def refresh(body:Refresh,request:Request):
        throttle(request,'refresh')
        token=rooms.restore_device(body.device_token)
        if not token:raise HTTPException(401,'Entre novamente para sincronizar; os dados offline continuam no aparelho.')
        return activated(token)

    @app.post('/v1/sync')
    def sync(body:SyncBody,request:Request):
        token=bearer(request)
        try:return mobile_sync.sync(token,body.device,body.events,body.platform,body.version)
        except ValueError as error:raise HTTPException(409,str(error)) from None
        except PermissionError as error:raise HTTPException(403,str(error)) from None

    @app.get('/v1/sync/checkpoints')
    def checkpoints(request:Request):
        try:return {'devices':mobile_sync.checkpoints(bearer(request))}
        except PermissionError:raise HTTPException(403,'Acesso revogado.') from None

    return app


app=create_app()

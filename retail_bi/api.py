"""Superset REST client. Credentials/tokens are never printed or persisted."""
from datetime import timedelta
import json
import os
import subprocess
import uuid
import requests
from .config import ROOT,MARKER

NAMESPACE=uuid.UUID('6ebbe808-c7cf-4c5d-a002-fd97ccae369d')


def uid(key):return str(uuid.uuid5(NAMESPACE,key))


class API:
    def __init__(self):
        self.base=os.getenv('SUPERSET_URL','http://127.0.0.1:8088').rstrip('/')
        self.s=requests.Session(); self._lists={}
        token=os.getenv('SUPERSET_ACCESS_TOKEN')
        if not token and os.getenv('SUPERSET_PASSWORD'):
            r=self.s.post(self.base+'/api/v1/security/login',json=dict(username=os.getenv('SUPERSET_USERNAME','admin'),password=os.environ['SUPERSET_PASSWORD'],provider='db'),timeout=30)
            if not r.ok:raise RuntimeError('Superset sign-in failed')
            token=r.json()['access_token']
        if not token:
            container=os.getenv('SUPERSET_DOCKER_CONTAINER')
            if not container:raise RuntimeError('Set Superset credentials, token, or authorized local Docker container')
            script='''from datetime import timedelta
from superset.app import create_app
from flask_jwt_extended import create_access_token
app=create_app()
with app.app_context():
    sm=app.appbuilder.sm
    user=sm.find_user(username="admin")
    if not user or not user.active or "Admin" not in [r.name for r in user.roles]:
        raise RuntimeError("An existing active local admin is required")
    print("RETAIL_AUTH="+create_access_token(identity=str(user.id),expires_delta=timedelta(hours=2)))
'''
            proc=subprocess.run(['docker','exec','-i',container,'/app/.venv/bin/python','-'],input=script,text=True,capture_output=True)
            matches=[line.split('=',1)[1] for line in proc.stdout.splitlines() if line.startswith('RETAIL_AUTH=')]
            if proc.returncode or len(matches)!=1:raise RuntimeError('Unable to obtain temporary local Superset session')
            token=matches[0]
        self.s.headers['Authorization']='Bearer '+token
        self.s.headers['X-CSRFToken']=self.request('GET','security/csrf_token/')['result']
        self.s.headers['Referer']=self.base+'/'

    def request(self,method,path,**kwargs):
        response=self.s.request(method,self.base+'/api/v1/'+path,timeout=120,**kwargs)
        if not response.ok:
            error={}
            try:error=response.json()
            except ValueError:pass
            fields=list(error.get('message',{})) if isinstance(error.get('message'),dict) else []
            # SQL errors are deliberately not echoed with URIs or credentials.
            raise RuntimeError(f'Superset {method} {path}: HTTP {response.status_code}; fields={fields}')
        if response.headers.get('Content-Type','').startswith('application/zip'):return response.content
        return response.json()

    def all(self,kind):
        if kind in self._lists:return self._lists[kind]
        rows=[];page=0
        while True:
            result=self.request('GET',kind+'/',params={'q':f'(page:{page},page_size:100)'})
            rows.extend(result['result'])
            if len(rows)>=result['count']:break
            page+=1
        self._lists[kind]=rows
        return rows

    def upsert(self,kind,key,payload):
        identity=uid(kind+':'+key)
        matches=[row for row in self.all(kind) if row.get('uuid')==identity]
        if len(matches)>1:raise RuntimeError('Duplicate project UUID')
        if matches:
            ident=matches[0]['id']
            current=self.request('GET',f'{kind}/{ident}')['result']
            if current.get('description') and not current['description'].startswith(MARKER):raise RuntimeError('Ownership marker mismatch')
            self.request('PUT',f'{kind}/{ident}',json={**payload,'uuid':identity})
        else:
            ident=self.request('POST',kind+'/',json={**payload,'uuid':identity})['id']
            self._lists[kind].append({'id':ident,'uuid':identity})
        return ident

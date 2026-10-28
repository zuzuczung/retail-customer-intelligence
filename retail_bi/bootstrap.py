"""Create project-owned roles/database in the existing local PostgreSQL container."""
from pathlib import Path
import json
import os
import secrets
import subprocess
from dotenv import dotenv_values,load_dotenv

ROOT=Path(__file__).resolve().parents[1]
MARKER='retail-customer-intelligence:v1'


def psql(statement, database='postgres'):
    result=subprocess.run(['docker','exec','-i','postgres-local','sh','-c',
        'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -At','sh',database],
        input=statement,text=True,capture_output=True,check=False)
    if result.returncode:
        raise RuntimeError('Project PostgreSQL bootstrap failed; no credentials logged')
    return result.stdout.strip()


def main():
    env=ROOT/'.env'
    if not env.exists():
        env.write_text('PGHOST=127.0.0.1\nPGPORT=5432\nPGDATABASE=retail_customer_intelligence\nPGUSER=retail_bi\nPGPASSWORD='+secrets.token_urlsafe(30)+'\nSUPERSET_DATABASE_USER=retail_reader\nSUPERSET_DATABASE_PASSWORD='+secrets.token_urlsafe(30)+'\nSUPERSET_URL=http://127.0.0.1:8088\nSUPERSET_DOCKER_CONTAINER=superset_app\n')
        env.chmod(0o600)
    values=dotenv_values(env)
    for role,key in [('retail_bi','PGPASSWORD'),('retail_reader','SUPERSET_DATABASE_PASSWORD')]:
        marker=psql("SELECT coalesce(shobj_description(oid,'pg_authid'),'') FROM pg_roles WHERE rolname='"+role+"'")
        exists=psql("SELECT count(*) FROM pg_roles WHERE rolname='"+role+"'")=='1'
        if exists and marker!=MARKER:raise RuntimeError('Unowned role collision')
        if not exists:
            password=values[key]
            if not password or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in password):raise ValueError('Unexpected generated password encoding')
            psql(f"BEGIN; CREATE ROLE {role} LOGIN PASSWORD '{password}'; COMMENT ON ROLE {role} IS '{MARKER}'; COMMIT;")
    db='retail_customer_intelligence'
    exists=psql(f"SELECT count(*) FROM pg_database WHERE datname='{db}'")=='1'
    if exists:
        marker=psql(f"SELECT coalesce(shobj_description(oid,'pg_database'),'') FROM pg_database WHERE datname='{db}'")
        if marker!=MARKER:raise RuntimeError('Unowned database collision')
    else:
        psql('CREATE DATABASE retail_customer_intelligence OWNER retail_bi;')
        psql(f"COMMENT ON DATABASE retail_customer_intelligence IS '{MARKER}';")
    psql('REVOKE CONNECT ON DATABASE retail_customer_intelligence FROM PUBLIC; GRANT CONNECT ON DATABASE retail_customer_intelligence TO retail_bi,retail_reader;')
    load_dotenv(env)
    print('Project database and read-only BI role ready.')


if __name__=='__main__':main()

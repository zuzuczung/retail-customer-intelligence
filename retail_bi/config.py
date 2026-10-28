from pathlib import Path
import os
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
MARKER='retail-customer-intelligence:v1'


def database_kwargs():
    return dict(host=os.getenv('PGHOST','127.0.0.1'),port=int(os.getenv('PGPORT','5432')),
                dbname=os.getenv('PGDATABASE','retail_customer_intelligence'),
                user=os.getenv('PGUSER','retail_bi'),password=os.environ['PGPASSWORD'])

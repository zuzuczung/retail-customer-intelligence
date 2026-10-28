"""Atomic source load + project-only transforms + independent reconciliations."""
from decimal import Decimal
import json
import hashlib
import psycopg
from .config import ROOT,database_kwargs


def connect():return psycopg.connect(**database_kwargs())


def query(sql,params=None):
    with connect() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql,params)
            return cur.fetchall()


def main():
    profile=json.loads((ROOT/'artifacts/source-profile.json').read_text())
    source=ROOT/'data/interim/online-retail.csv'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=profile['csv_sha256']:raise RuntimeError('CSV differs from the independently controlled source')
    with connect() as conn:
        conn.execute((ROOT/'sql/01_staging.sql').read_text())
        conn.execute('TRUNCATE staging.invoice_line')
        with conn.cursor().copy("COPY staging.invoice_line FROM STDIN WITH (FORMAT CSV,HEADER TRUE,NULL '__RETAIL_NULL_SENTINEL__')") as copy:
            with source.open('rb') as f:
                while chunk:=f.read(1024*1024):copy.write(chunk)
        conn.execute('INSERT INTO staging.load_audit(source_sha256,row_count,source_url) VALUES(%s,%s,%s)',(profile['xlsx_sha256'],profile['counts']['source_rows'],profile['source']))
        conn.execute((ROOT/'sql/02_analytics.sql').read_text())
    print('Staging and analytics loaded; transaction committed.')
    validate()


def validate():
    p=json.loads((ROOT/'artifacts/source-profile.json').read_text())
    checks=[]
    def check(name,actual,expected):
        ok=actual==expected;checks.append(dict(name=name,actual=str(actual),expected=str(expected),passed=ok))
    facts=query('SELECT count(*) AS orders,sum(sales_amount) AS gross,count(DISTINCT customer_id) AS customers FROM analytics.fact_order')[0]
    check('source rows',query('SELECT count(*) n FROM staging.invoice_line')[0]['n'],p['counts']['source_rows'])
    check('sales invoices',facts['orders'],p['sales_invoices'])
    check('gross source to orders',facts['gross'],Decimal(p['gross_sales_gbp']))
    check('gross lines to orders',query('SELECT sum(sales_amount) n FROM analytics.fact_line')[0]['n'],facts['gross'])
    check('known customers',facts['customers'],p['known_customers'])
    check('snapshot customers',query('SELECT count(*) n FROM analytics.customer_rfm')[0]['n'],facts['customers'])
    check('negative adjustments',query('SELECT -sum(adjustment_amount) n FROM analytics.v_adjustment')[0]['n'],Decimal(p['negative_adjustments_gbp']))
    actual_classes={r['line_class']:r['n'] for r in query('SELECT line_class,count(*) n FROM analytics.classified_line GROUP BY 1')}
    for kind,sourcekey in [('duplicate','duplicate_rows'),('sale','sale'),('negative_adjustment','negative_adjustment'),('non_merchandise','non_merchandise'),('invalid_price','invalid_price'),('other','other')]:
        check('classification '+kind,actual_classes.get(kind,0),p['counts'].get(sourcekey,0))
    invariants={
      'order grain attributes':'''SELECT count(*) n FROM (SELECT invoice_no FROM analytics.fact_line GROUP BY invoice_no HAVING count(DISTINCT purchased_at)>1 OR count(DISTINCT customer_id)>1 OR count(DISTINCT country)>1) t''',
      'orphan product':'''SELECT count(*) n FROM analytics.fact_line l LEFT JOIN analytics.dim_product p USING(stock_code) WHERE p.stock_code IS NULL''',
      'cohort invalid rate':'''SELECT count(*) n FROM analytics.cohort_retention WHERE active_customers<0 OR active_customers>cohort_size OR retention_rate<0 OR retention_rate>1''',
      'cohort M0':'''SELECT count(*) n FROM analytics.cohort_retention WHERE age_month=0 AND active_customers<>cohort_size''',
      'cohort immature':'''SELECT count(*) n FROM analytics.cohort_retention WHERE activity_month>last_complete_month''',
      'RFM nonpositive purchases':'''SELECT count(*) n FROM analytics.customer_rfm WHERE frequency<1 OR monetary<=0 OR recency_days<1''',
    }
    for name,sql in invariants.items():check(name,query(sql)[0]['n'],0)
    profile={
      'classes':actual_classes,'checks':checks,
      'totals':facts,
      'coverage':query('SELECT min(purchased_at) first_date,max(purchased_at) last_date,count(*) FILTER(WHERE customer_id IS NULL) anonymous_orders,sum(sales_amount) FILTER(WHERE customer_id IS NULL) anonymous_sales FROM analytics.fact_order')[0],
      'segments':query('SELECT segment,count(*) customers,sum(monetary) sales FROM analytics.customer_rfm GROUP BY 1 ORDER BY 2 DESC'),
      'invoice_time_normalization':query('SELECT count(DISTINCT invoice_no) n FROM analytics.fact_line WHERE purchased_at<>source_purchased_at')[0]['n'],
      'country_changes':query('SELECT count(*) n FROM analytics.fact_line WHERE country<>transaction_country')[0]['n'],
      'cohort_last_complete_month':query('SELECT max(last_complete_month) n FROM analytics.cohort_retention')[0]['n'],
      'top_products':query('SELECT stock_code,max(product_name) product,sum(sales_amount) sales FROM analytics.fact_line GROUP BY 1 ORDER BY 3 DESC LIMIT 5'),
      'outlier_lines':query('SELECT invoice_no,stock_code,quantity,unit_price,sales_amount FROM analytics.fact_line ORDER BY sales_amount DESC LIMIT 5'),
    }
    (ROOT/'artifacts/data-validation.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2,default=str)+'\n')
    failed=[c['name'] for c in checks if not c['passed']]
    if failed:raise RuntimeError('Validation failed: '+', '.join(failed))
    print(json.dumps({'passed':len(checks),'totals':facts,'coverage':profile['coverage']},ensure_ascii=False,default=str))


if __name__=='__main__':main()

-- The whole file runs in one transaction, within this project's dedicated database.
DROP SCHEMA IF EXISTS analytics CASCADE;
CREATE SCHEMA analytics;

CREATE TABLE analytics.classified_line AS
WITH ranked AS (
 SELECT *,row_number() OVER (
  PARTITION BY invoice_no,stock_code,description,quantity,invoice_date,unit_price,customer_id,country
  ORDER BY source_row) AS duplicate_rank
 FROM staging.invoice_line
)
SELECT source_row,invoice_no,stock_code,nullif(btrim(description),'') AS description,
 quantity::integer AS quantity, invoice_date::timestamp AS purchased_at,
 unit_price::numeric(18,6) AS unit_price,
 CASE WHEN customer_id='' THEN NULL ELSE customer_id::numeric::bigint::text END AS customer_id,
 coalesce(nullif(btrim(country),''),'Không rõ') AS transaction_country,
 quantity::numeric * unit_price::numeric AS line_value,
 CASE WHEN duplicate_rank>1 THEN 'duplicate'
      WHEN stock_code !~ '^[0-9]{5}[A-Za-z]*$' THEN 'non_merchandise'
      WHEN unit_price::numeric<=0 THEN 'invalid_price'
      WHEN quantity::integer>0 AND upper(invoice_no) NOT LIKE 'C%' THEN 'sale'
      WHEN quantity::integer<0 THEN 'negative_adjustment'
      ELSE 'other' END AS line_class
FROM ranked;
ALTER TABLE analytics.classified_line ADD PRIMARY KEY(source_row);
CREATE INDEX ON analytics.classified_line(line_class);

CREATE TABLE analytics.dim_customer AS
SELECT DISTINCT ON(customer_id) customer_id,transaction_country AS country,purchased_at AS first_purchased_at,
 date_trunc('month',purchased_at)::date AS cohort_month
FROM analytics.classified_line
WHERE line_class='sale' AND customer_id IS NOT NULL
ORDER BY customer_id,purchased_at,invoice_no,source_row;
ALTER TABLE analytics.dim_customer ADD PRIMARY KEY(customer_id);

CREATE TABLE analytics.dim_product AS
SELECT DISTINCT ON(stock_code) stock_code,coalesce(description,stock_code) AS product_name
FROM analytics.classified_line
WHERE line_class='sale'
ORDER BY stock_code,(description IS NOT NULL) DESC,purchased_at DESC,source_row DESC;
ALTER TABLE analytics.dim_product ADD PRIMARY KEY(stock_code);

CREATE TABLE analytics.fact_line AS
SELECT l.source_row,l.invoice_no,l.stock_code,p.product_name,l.stock_code||' · '||p.product_name AS product_label,l.quantity,l.unit_price,
 l.line_value AS sales_amount,min(l.purchased_at) OVER(PARTITION BY l.invoice_no) AS purchased_at,
 l.purchased_at AS source_purchased_at,l.customer_id,
 coalesce(c.country,l.transaction_country) AS country,l.transaction_country
FROM analytics.classified_line l
JOIN analytics.dim_product p USING(stock_code)
LEFT JOIN analytics.dim_customer c USING(customer_id)
WHERE l.line_class='sale';
ALTER TABLE analytics.fact_line ADD PRIMARY KEY(source_row);
CREATE INDEX ON analytics.fact_line(purchased_at);
CREATE INDEX ON analytics.fact_line(country,purchased_at);

CREATE TABLE analytics.fact_order AS
SELECT invoice_no,min(purchased_at) AS purchased_at,min(customer_id) AS customer_id,
 min(country) AS country,sum(quantity) AS units,sum(sales_amount) AS sales_amount,
 count(*) AS line_count,count(DISTINCT stock_code) AS distinct_products
FROM analytics.fact_line GROUP BY invoice_no;
ALTER TABLE analytics.fact_order ADD PRIMARY KEY(invoice_no);
CREATE INDEX ON analytics.fact_order(purchased_at);
CREATE INDEX ON analytics.fact_order(country,purchased_at);

CREATE VIEW analytics.v_adjustment AS
SELECT l.source_row,l.invoice_no,l.purchased_at,l.customer_id,coalesce(c.country,l.transaction_country) AS country,
 -l.line_value AS adjustment_amount
FROM analytics.classified_line l LEFT JOIN analytics.dim_customer c USING(customer_id)
WHERE l.line_class='negative_adjustment';

CREATE TABLE analytics.customer_rfm AS
WITH snapshot AS (SELECT max(invoice_date::timestamp)::date+1 AS snapshot_date FROM staging.invoice_line),
 base AS (
  SELECT o.customer_id,c.country,c.cohort_month,s.snapshot_date::timestamp AS snapshot_at,
   s.snapshot_date-max(o.purchased_at)::date AS recency_days,
   count(*)::integer AS frequency,sum(o.sales_amount) AS monetary,
   min(o.purchased_at) AS first_purchased_at,max(o.purchased_at) AS last_purchased_at
  FROM analytics.fact_order o JOIN analytics.dim_customer c USING(customer_id) CROSS JOIN snapshot s
  GROUP BY o.customer_id,c.country,c.cohort_month,s.snapshot_date
 ), scored AS (
  SELECT *,CASE WHEN recency_days<=30 THEN 5 WHEN recency_days<=60 THEN 4 WHEN recency_days<=90 THEN 3 WHEN recency_days<=180 THEN 2 ELSE 1 END AS r_score,
   CASE WHEN frequency>=10 THEN 5 WHEN frequency>=6 THEN 4 WHEN frequency>=3 THEN 3 WHEN frequency>=2 THEN 2 ELSE 1 END AS f_score,
   CASE WHEN monetary>=5000 THEN 5 WHEN monetary>=2000 THEN 4 WHEN monetary>=1000 THEN 3 WHEN monetary>=500 THEN 2 ELSE 1 END AS m_score
  FROM base
 )
SELECT *,r_score::text||f_score::text||m_score::text AS rfm_score,
 CASE WHEN r_score>=4 AND f_score>=4 AND m_score>=3 THEN 'Giá trị cao'
      WHEN r_score>=3 AND f_score>=3 THEN 'Thân thiết'
      WHEN r_score<=2 AND f_score>=3 THEN 'Có nguy cơ rời bỏ'
      WHEN r_score<=2 THEN 'Ngủ đông'
      ELSE 'Đang phát triển' END AS segment
FROM scored;
ALTER TABLE analytics.customer_rfm ADD PRIMARY KEY(customer_id);

CREATE TABLE analytics.cohort_retention AS
WITH cutoff AS (
 SELECT CASE WHEN max(invoice_date::timestamp)::date=(date_trunc('month',max(invoice_date::timestamp))+interval '1 month - 1 day')::date
  THEN date_trunc('month',max(invoice_date::timestamp))::date
  ELSE (date_trunc('month',max(invoice_date::timestamp))-interval '1 month')::date END AS last_complete_month
 FROM staging.invoice_line
), cohort AS (
 SELECT c.cohort_month,c.country,count(*)::integer AS cohort_size
 FROM analytics.dim_customer c CROSS JOIN cutoff x
 WHERE c.cohort_month<=x.last_complete_month GROUP BY c.cohort_month,c.country
), scaffold AS (
 SELECT c.*,a.age_month,(c.cohort_month+(a.age_month||' months')::interval)::date AS activity_month,x.last_complete_month
 FROM cohort c CROSS JOIN cutoff x
 CROSS JOIN LATERAL generate_series(0,(extract(year FROM age(x.last_complete_month,c.cohort_month))*12+extract(month FROM age(x.last_complete_month,c.cohort_month)))::integer) a(age_month)
), activity AS (
 SELECT c.cohort_month,c.country,date_trunc('month',o.purchased_at)::date AS activity_month,
  count(DISTINCT o.customer_id)::integer AS active_customers
 FROM analytics.fact_order o JOIN analytics.dim_customer c USING(customer_id)
 CROSS JOIN cutoff x
 WHERE o.purchased_at<x.last_complete_month+interval '1 month'
 GROUP BY c.cohort_month,c.country,date_trunc('month',o.purchased_at)::date
)
SELECT s.cohort_month::timestamp AS cohort_month,s.country,s.cohort_size,s.age_month,
 'M'||lpad(s.age_month::text,2,'0') AS age_label,s.activity_month,
 coalesce(a.active_customers,0)::integer AS active_customers,
 coalesce(a.active_customers,0)::numeric/s.cohort_size AS retention_rate,s.last_complete_month
FROM scaffold s LEFT JOIN activity a USING(cohort_month,country,activity_month);
ALTER TABLE analytics.cohort_retention ADD PRIMARY KEY(cohort_month,country,age_month);

CREATE TABLE analytics.dim_date AS
SELECT d::date AS calendar_date,extract(year FROM d)::integer AS year,extract(month FROM d)::integer AS month,
 to_char(d,'YYYY-MM') AS year_month
FROM generate_series((SELECT min(purchased_at)::date FROM analytics.fact_order),
 (SELECT max(purchased_at)::date FROM analytics.fact_order),interval '1 day') d;
ALTER TABLE analytics.dim_date ADD PRIMARY KEY(calendar_date);

COMMENT ON SCHEMA analytics IS 'retail-customer-intelligence:v1';
GRANT USAGE ON SCHEMA analytics TO retail_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO retail_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO retail_reader;
ANALYZE;

CREATE SCHEMA IF NOT EXISTS staging;
CREATE TABLE IF NOT EXISTS staging.invoice_line (
 source_row integer PRIMARY KEY, invoice_no text NOT NULL,stock_code text NOT NULL,
 description text NOT NULL,quantity text NOT NULL,invoice_date text NOT NULL,
 unit_price text NOT NULL,customer_id text NOT NULL,country text NOT NULL
);
CREATE TABLE IF NOT EXISTS staging.load_audit (
 loaded_at timestamptz NOT NULL DEFAULT now(), source_sha256 text NOT NULL,
 row_count integer NOT NULL, source_url text NOT NULL
);

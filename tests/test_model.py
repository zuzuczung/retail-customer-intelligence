"""Integration checks against the dedicated project database; no writes."""
import unittest
from retail_bi.pipeline import query
from retail_bi.rules import rfm_scores


class ModelTests(unittest.TestCase):
    def test_invoice_timestamp_normalization(self):
        rows=query('''SELECT count(*) n FROM analytics.fact_line l JOIN (
         SELECT invoice_no,min(source_purchased_at) earliest FROM analytics.fact_line GROUP BY invoice_no
        ) i USING(invoice_no) WHERE l.purchased_at<>i.earliest''')
        self.assertEqual(rows[0]['n'],0)

    def test_customer_country_assignment(self):
        self.assertEqual(query('''SELECT count(*) n FROM analytics.fact_line l JOIN analytics.dim_customer c USING(customer_id) WHERE l.country<>c.country''')[0]['n'],0)

    def test_cohort_maturity_and_zeros(self):
        self.assertEqual(query("SELECT count(*) n FROM analytics.cohort_retention WHERE activity_month>='2011-12-01'")[0]['n'],0)
        self.assertGreater(query('SELECT count(*) n FROM analytics.cohort_retention WHERE active_customers=0')[0]['n'],0)
        self.assertEqual(query('SELECT count(*) n FROM analytics.cohort_retention WHERE age_month=0 AND retention_rate<>1')[0]['n'],0)

    def test_rfm_sql_matches_independent_python_boundaries(self):
        rows=query('SELECT recency_days,frequency,monetary,r_score,f_score,m_score FROM analytics.customer_rfm')
        for row in rows:
            self.assertEqual(rfm_scores(row['recency_days'],row['frequency'],row['monetary']),(row['r_score'],row['f_score'],row['m_score']))


if __name__=='__main__':unittest.main()

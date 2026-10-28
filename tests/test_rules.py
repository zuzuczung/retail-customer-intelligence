from decimal import Decimal
import unittest
from retail_bi.rules import classify,rfm_scores


class RuleTests(unittest.TestCase):
    def test_regular_sale(self):
        self.assertEqual(classify('536365','85123A',6,Decimal('2.55')),'sale')

    def test_negative_adjustment_without_c_prefix(self):
        self.assertEqual(classify('536365','85123A',-6,Decimal('2.55')),'negative_adjustment')

    def test_cancellation_is_not_gross_sale(self):
        self.assertEqual(classify('C536365','85123A',6,Decimal('2.55')),'other')

    def test_postage_and_manual_adjustments_are_not_products(self):
        for code in ['POST','DOT','M','BANK CHARGES','gift_0001']:
            with self.subTest(code=code):self.assertEqual(classify('536365',code,6,Decimal('2.55')),'non_merchandise')

    def test_zero_and_negative_price(self):
        for price in [Decimal('0'),Decimal('-1')]:
            self.assertEqual(classify('536365','85123A',1,price),'invalid_price')

    def test_rfm_threshold_boundaries(self):
        self.assertEqual(rfm_scores(30,10,Decimal('5000')),(5,5,5))
        self.assertEqual(rfm_scores(31,9,Decimal('4999.99')),(4,4,4))
        self.assertEqual(rfm_scores(90,3,Decimal('1000')),(3,3,3))
        self.assertEqual(rfm_scores(91,2,Decimal('999.99')),(2,2,2))
        self.assertEqual(rfm_scores(181,1,Decimal('499.99')),(1,1,1))


if __name__=='__main__':unittest.main()

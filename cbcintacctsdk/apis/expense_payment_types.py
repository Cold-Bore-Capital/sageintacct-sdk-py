"""
Sage Intacct Expense Payment Types
"""
from typing import Dict

from .api_base import ApiBase


class ExpensePaymentTypes(ApiBase):
    """Class for Expense Payment Types APIs."""
    def __init__(self):
        super().__init__(dimension='EXPENSEPAYMENTTYPE')

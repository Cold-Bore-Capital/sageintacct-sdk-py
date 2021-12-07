"""
Sage Intacct AR Invoice
"""

from .api_base import ApiBase


class ARInvoices(ApiBase):
    """Class for AR Invoice APIs."""
    def __init__(self):
        super().__init__(dimension='ARINVOICE', post_legacy_method='create_invoice')

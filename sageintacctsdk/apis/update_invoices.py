"""
Sage Intacct AR Invoice
"""

from .api_base import ApiBase


class UpdateInvoices(ApiBase):
    """Class to update invoice details"""
    def __init__(self):
        ApiBase.__init__(self, dimension='update_invoice', post_legacy_method='update_invoice')

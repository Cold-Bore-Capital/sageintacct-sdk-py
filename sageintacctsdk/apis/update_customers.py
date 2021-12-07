"""
Sage Intacct AR Invoice
"""

from .api_base import ApiBase


class UpdateCustomers(ApiBase):
    """Class to update customer details."""
    def __init__(self):
        super().__init__(dimension='update_customer', post_legacy_method='update_customer')

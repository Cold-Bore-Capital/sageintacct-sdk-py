"""
Sage Intacct AR Invoice
"""

from .api_base import ApiBase


class ARAdjustment(ApiBase):
    """Class for AR Invoice APIs."""
    def __init__(self):
        ApiBase.__init__(self, dimension='create_aradjustment', post_legacy_method='create_aradjustment')

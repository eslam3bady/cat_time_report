# -*- coding: utf-8 -*-

from odoo import models, fields, api
from itertools import groupby
from operator import itemgetter
#
#
# class PurchaseOrder(models.Model):
#     _inherit = "purchase.order"
#     po_by_vendor=fields.Boolean('')

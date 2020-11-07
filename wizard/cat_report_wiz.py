# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class ProductVariantWizard(models.TransientModel):
    _name = 'cat_time.report.wiz'
    _description = 'Cat Sales Report'

    date_from = fields.Date('Date From', )
    date_to = fields.Date('Date To', )
    select_month = fields.Date(string='Select Start', )
    select_month_end = fields.Date(string='Select End', )


    compute_at_date = fields.Selection([
        (0, 'Current'),
        (1, 'At a Specific Period')], default=0)
    sorting_type = fields.Selection(string="Sorting",
                                    selection=[('qty', 'تقرير بيع المجموعات عدد'),
                                               ('value', 'تقرير بيع المجموعات قيمة'),
                                               ],
                                    required=True,default='qty')

    branches = fields.Selection(string="", selection=[('all', 'All Company'), ('branch', 'By Branch'), ],
                                required=False,default='all')
    branch_ids = fields.Many2many(comodel_name="stock.warehouse", string="Branches", )
    categs = fields.Selection(string="", selection=[('all', 'All Categories'), ('categ', 'By Category'), ],
                              required=False,default='all')
    categ_ids = fields.Many2many(comodel_name="product.category",  string="Categories", )
    vendor = fields.Selection(string="", selection=[('all', 'All Vendors'), ('vendor', 'By Vendor'), ],
                              required=False,default='all')
    vendor_ids = fields.Many2many(comodel_name="res.partner", string="Vendors", domain=[('supplier', '=', True)])

    def _print_report_xlsx(self, data):
        return self.env.ref('cat_time_report.action_report_cat_time_csv').report_action(self, data)

    @api.onchange('vendor')
    def set_vendors(self):
        if self.vendor:
            self.vendor_ids=False

    @api.onchange('branches')
    def set_branches(self):
        if self.branches:
            self.branch_ids = False

    @api.onchange('categs')
    def set_cats(self):
        if self.categs:
            self.categ_ids = False

    @api.onchange('compute_at_date')
    def set_dates(self):
        if self.compute_at_date:
            self.date_to = False
            self.date_from = False

    @api.onchange('categs')
    def set_categs(self):
        if self.categs:
            self.categ_ids = False
    @api.multi
    def view_report_xlsx(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['compute_at_date'] = self.compute_at_date
        data['sorting'] = self.sorting_type
        data['branches'] = self.branches
        data['categs'] = self.categs
        data['vendor'] = self.vendor
        data['select_month'] = self.select_month
        data['select_month_end'] = self.select_month_end
        data['branch_ids'] = self.branch_ids.ids
        data['categ_ids'] = self.categ_ids.ids
        data['vendor_ids'] = self.vendor_ids.ids
        if self.date_from and self.date_to:
            data['date_from'] = self.date_from
            data['date_to'] = self.date_to
        return self._print_report_xlsx(data)

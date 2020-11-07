# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import collections
from datetime import timedelta, datetime, date
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class ProductVariantReport(models.AbstractModel):
    _name = "report.cat_time_report.sales_report"
    _inherit = "report.report_xlsx.abstract"
    def _get_warehouse(self,branches,branches_ids):
        if branches == 'all':
            warehouses=self.env['stock.warehouse'].search([])
        else:
            warehouses=self.env['stock.warehouse'].search([('id','in',branches_ids)])
        return warehouses

    def _get_gategory(self, categs, categ_ids, vendors, vendors_ids):
        product_ids = []
        if categs == 'all':
            ids = []
            vendor_id = []
            if vendors == 'all':
                for rec in self.env['product.product'].search([('categ_id', '!=', False)]):
                    ids.append(rec.categ_id.id)
                    product_ids.append(rec.id)
                cats = self.env['product.category'].search([('id', 'in', ids)])
            else:
                for rec in self.env['product.product'].search([('categ_id', '!=', False)]):
                    vendor = self.env['product.supplierinfo'].search([('product_tmpl_id', '=', rec.product_tmpl_id.id)],
                                                                     order='id', limit=1)
                    if vendor.name.id in vendors_ids:
                        ids.append(rec.categ_id.id)
                        product_ids.append(rec.id)

                cats = self.env['product.category'].search([('id', 'in', ids)])
        else:
            ids = []
            if vendors == 'all':
                cats = self.env['product.category'].search([('id', '=', categ_ids)])
                product_ids = self.env['product.product'].search([('categ_id', 'in', categ_ids)]).ids
            else:
                for rec in self.env['product.product'].search(
                        [('categ_id', 'in', categ_ids)]):
                    vendor = self.env['product.supplierinfo'].search([('product_tmpl_id', '=', rec.product_tmpl_id.id)],
                                                                     order='id', limit=1)
                    if vendor.name.id in vendors_ids:
                        ids.append(rec.categ_id.id)
                        product_ids.append(rec.id)
                cats = self.env['product.category'].search([('id', 'in', ids)])
        return [cats, product_ids]

    def _get_products(self, vendors, vendors_ids):
        vendor_product_dict = {}
        if vendors == 'all':
            for vendor in self.env['res.partner'].search([('supplier', '=', True)]):
                product_ids = []
                for rec in self.env['product.template'].search([]):
                    num_attrs = len(rec.seller_ids)
                    vendor_rec = self.env['product.supplierinfo'].search(
                        [('product_tmpl_id', '=', rec.id)], order='id', limit=1)
                    if vendor.id == vendor_rec.name.id:
                        product_ids.append(rec.id)
                vendor_product_dict[vendor.id] = product_ids

        else:
            for vendor_id in vendors_ids:
                product_ids = []
                for rec in self.env['product.template'].search([]):
                    num_attrs = len(rec.seller_ids)
                    vendor_rec = self.env['product.supplierinfo'].search([('product_tmpl_id', '=', rec.id)], order='id',
                                                                         limit=1)
                    if vendor_id == vendor_rec.name.id:
                        product_ids.append(rec.id)
                vendor_product_dict[vendor_id] = product_ids
        return vendor_product_dict
    def get_quantitiy(self,domain,sorting):
        qty=0.0
        onhand=0.0
        onhand_value=0.0
        q_dict={}
        if sorting=='branch':
            for quant in self.env['stock.quant'].search(domain):
                print('55555555')
                qty += quant.product_id.sales_count
                onhand += quant.quantity
                onhand_value += (quant.quantity * quant.product_id.standard_price)
            q_dict = {'qty':qty,'onhand':onhand,'onhand_value':onhand_value}
        else:
            for quant in self.env['product.product'].search(domain):
                qty += quant.sales_count
                onhand += quant.qty_available
                onhand_value += (quant.qty_available * quant.standard_price)
            q_dict = {'qty': qty, 'onhand': onhand, 'onhand_value': onhand_value}

        return q_dict
    def get_sales(self,sale_order_domain,pos_domain):
        sale_amount = 0.0
        sale_in_cost = 0.0
        return_sale_amount = 0.0
        sale_qty, return_sale_qty = 0.0, 0.0
        order_count=0
        order_amount=0.0

        for order in self.env['sale.order.line'].search(
                sale_order_domain):
            if self.env['stock.picking'].search([('id', 'in', order.order_id.picking_ids.ids),
                                                 ('picking_type_id.name', '=', 'Delivery Orders')],
                                                limit=1).state == 'done':
                order_count+=1
                sale_amount += order.price_subtotal
                # sale_in_cost += (order.amount_total - order.margin)
                sale_qty = order.product_uom_qty
                # sale_qty_value += order.price_subtotal
            for move in self.env['stock.move'].search(
                    [('picking_id.picking_type_id.name', '=', 'Receipts'),
                     ('picking_id.state', '=', 'done'),
                     ('product_id', '=', order.product_id.id),
                     ('picking_id.partner_id', '=', order.order_id.partner_id.id),
                     ('picking_id', 'in', order.order_id.picking_ids.ids)]):
                sale_qty -= move.product_uom_qty
                # line_id = order.order_line.filtered(lambda l: l.product_id.id == move.product_id.id)
                return_sale_amount += (move.product_uom_qty * order.price_unit)
            sale_in_cost += (sale_qty - return_sale_qty) * order.purchase_price

        for order in self.env['pos.order.line'].search(pos_domain):
            order_count+=1
            sale_qty += order.qty
            # sale_in_cost += (order.qty * order.purchase_price)
            sale_amount += order.price_subtotal_incl
            for ret in self.env['pos.order.line'].search(
                    [('order_id.return_ref', '=', order.order_id.pos_reference),
                     ('product_id', '=', order.product_id.id)]):
                return_sale_amount += (ret.price_subtotal_incl * -1)
                # cost_return += ((ret.qty  * order.purchase_price)*-1)
                sale_qty +=ret.qty
        ach = sale_amount - return_sale_amount
        return {
            'qty_avg': sale_qty/order_count if order_count else 0.0,
            'value_avg': ach / order_count if order_count else 0.0,
            'orders':order_count
        }

    def _get_exel_report_data(self,data):
        profit_dict={}
        # sales_count_company = 0.0
        # branches = self._get_warehouse(data['branches'], data['branch_ids'])
        cats=self._get_gategory(data['categs'], data['categ_ids'],data['vendor'], data['vendor_ids'])
        fmt = '%m/%d/%Y'
        orders=0
        summ=0.0
        # for cat in cats[0]:
        if data['select_month']:
                select_m = datetime.strptime(data['select_month'], '%Y-%m-%d').date()
                select_m_end = datetime.strptime(data['select_month_end'], '%Y-%m-%d').date()
                s_date = select_m
                print(data['select_month'])
                while select_m <= select_m_end:
                    sub_dict = {}
                    for cat in cats[0]:
                            # date=s_date.strftime('%Y-%m-%d')
                            sale_order_domain=[('product_id.categ_id', '=', cat.id),('product_id', 'in', cats[1]),
                            ('order_id.confirmation_date', '>=', s_date),
                                               ('order_id.confirmation_date', '<=', s_date)
                                               ]
                            pos_order_domain=[('product_id.categ_id', '=', cat.id),('product_id', 'in', cats[1]), ('order_id.return_ref', '=', False),
                                              ('order_id.date_order', '>=',s_date ),
                                              ('order_id.date_order', '<=', s_date)
                                              ]
                            sales_dict=self.get_sales(sale_order_domain,pos_order_domain)
                            print(sales_dict)
                            sub_dict[cat.name] = sales_dict
                    profit_dict[s_date] = sub_dict
                    select_m = select_m + relativedelta(days=1)
                    s_date = select_m
        return profit_dict

    @api.model
    def generate_xlsx_report(self, workbook, data, lines):
        header_dict = {'qty': 'تقرير مقارنة المجموعات عدد',
                       'value': 'تقرير مقارنة المجموعات قيمة'}

        lines=self._get_exel_report_data(data)
        if lines:
            format_1 = workbook.add_format({'font_size': 12, 'align': 'center'})
            format_1_date = workbook.add_format({'font_size': 12, 'align': 'center','bold': True,'num_format': 'd mmm '})

            format_2 = workbook.add_format({'font_size': 12, 'align': 'center','bold': True})
            center = workbook.add_format({'font_size': 12, 'align': 'center'})
            sheet = workbook.add_worksheet('Profit Report')
            sheet.right_to_left()
            sheet.set_column('A:F', 12)
            sheet.set_column('J:K', 18)
            sheet.set_page_view()
            sheet.merge_range(0, 0, 0, 4, header_dict[data['sorting']], center)
            # sum_qty=0.0
            # sum_sale,sum_cost,sum_onhand,sum_onhand_value,sum_profit=0.0,0.0,0.0,0.0,0.0
            #
            # if data['sorting'] in ['branch','vendor','cat']:
            #     for col in range(len(report_headers)):
            #         sheet.write(2, col + 1, report_headers[col], format_1)
            row_header = 3
            total_sum=0.0
            total_sum_value=0.0
            total_avg=0.0
            total_avg_value=0.0
            total_orders=0


            for k, val in lines.items():
                if data['sorting']=='value':
                    sheet.merge_range(row_header, 0, row_header + 1, 0, k, format_1_date)
                else:
                     sheet.write(row_header,0, k, format_1_date)
                sheet.write(2, len(list(val)) + 1, 'الاجمالى', format_1)
                sheet.write(2, len(list(val)) + 2, 'عدد الفواتير', format_1)
                sheet.write(2, len(list(val)) + 3, 'متوسط الفواتير', format_1)
                col_header = 1
                sum=0.0
                sum_value=0.0
                orders=0
                for key,v in val.items():
                    sheet.write(2, col_header, key, format_2)
                    sheet.write(row_header, col_header, v['qty_avg'], format_1)
                    if data['sorting'] == 'value':
                        sheet.write(row_header+1, col_header, v['value_avg'], format_1)
                    sum+=v['qty_avg']
                    total_sum+=sum
                    sum_value+=v['value_avg']
                    total_sum_value+=sum_value
                    orders+=v['orders']
                    total_orders+=orders
                    col_header+=1
                if orders == 0:
                    avg = 0.0
                    avg_value = 0.0

                else:
                    avg = (sum / orders) * 100
                    avg_value = (sum_value / orders) * 100
                total_avg+=avg
                total_avg_value+=avg_value
                if data['sorting']=='value':
                    sheet.write(row_header, col_header, sum, format_1)
                    sheet.write(row_header+1, col_header, sum_value, format_1)
                    sheet.merge_range(row_header, col_header+1, row_header + 1, col_header+1,orders, format_1)
                    sheet.write(row_header, col_header + 2, round(avg, 2), format_1)
                    sheet.write(row_header+1, col_header + 2, round(avg_value, 2), format_1)
                else:
                    sheet.write(row_header, col_header, sum, format_2)
                    sheet.write(row_header , col_header+1, orders, format_2)
                    sheet.write(row_header, col_header + 2, round(avg, 2), format_2)
                if data['sorting']=='value':
                    row_header+=2
                else:
                    row_header+=1
            dic={}
            cats=self._get_gategory(data['categs'], data['categ_ids'],data['vendor'], data['vendor_ids'])
            for cat in cats[0]:
                qty = 0.0
                value=0.0
                for k, val in lines.items():
                    for key, v in val.items():
                        if key == cat.name:
                            qty += v['qty_avg']
                            value+=v['value_avg']
                            dic[cat.name]=[qty,value]
            col_h=1
            for k1, v2 in dic.items():
                if data['sorting']=='value':
                    sheet.write(row_header, col_h, v2[0], format_2)
                    sheet.write(row_header+1, col_h, v2[1], format_2)
                else:
                    sheet.write(row_header, col_h, v2[0], format_2)
                col_h += 1
            if data['sorting'] == 'value':
                sheet.write(row_header, len(list(val)) + 1, total_sum, format_2)
                sheet.write(row_header + 1, len(list(val)) + 1, total_sum_value, format_2)
                sheet.merge_range(row_header, len(list(val)) + 2, row_header + 1, len(list(val)) + 2, total_orders, format_2)
                # sheet.write(row_header, len(list(val)) + 2, total_orders, format_2)
                sheet.write(row_header, len(list(val)) + 3, round(total_avg, 2), format_2)
                sheet.write(row_header + 1, len(list(val)) + 3, round(total_avg_value, 2), format_2)
            else:
                sheet.write(row_header, len(list(val)) + 1, total_sum, format_2)
                sheet.write(row_header, len(list(val)) + 2, total_orders, format_2)
                sheet.write(row_header, len(list(val)) + 3, round(total_avg, 2), format_2)

            #         sheet.write(row_header, col_header, val['qty'], format_1)
            #         sheet.write(row_header, col_header+1, val['sales'], format_1)
            #         sheet.write(row_header, col_header + 2, val['sale_in_cost'], format_1)
            #         sheet.write(row_header, col_header + 3, val['profit'], format_1)
            #         sheet.write(row_header, col_header + 4, val['onhand'], format_1)
            #         sheet.write(row_header, col_header + 5, val['onhand_value'], format_1)
            #         sheet.write(row_header, col_header + 6, round(val['gain_perc'], 2), format_1)
            #         sheet.write(row_header, col_header + 7, round(val['return_perc'], 2), format_1)
            #         sheet.write(row_header, col_header + 8, round(val['company_gain'], 2), format_1)
            #         sheet.write(row_header, col_header + 9, round(val['company_gain_perc'], 2), format_1)
            #         sheet.write(row_header, col_header + 10, val['qty_perc'], format_1)
            #         sum_qty += val['qty']
            #         sum_sale += val['sales']
            #         sum_cost += val['sale_in_cost']
            #         sum_onhand += val['onhand']
            #         sum_profit+=val['profit']
            #         sum_onhand_value += val['onhand_value']
            #         row_header += 1
            #     sheet.write(row_header, col_header + 1, sum_qty, format_2)
            #     sheet.write(row_header, col_header + 2, sum_sale, format_2)
            #     sheet.write(row_header, col_header + 3, sum_profit, format_2)
            #     sheet.write(row_header, col_header + 4, sum_onhand, format_2)
            #     sheet.write(row_header, col_header + 5, sum_onhand_value, format_2)
            #
            # elif data['sorting'] =='cat_details':
            #
            #     for col in range(len(report_headers)-4):
            #         sheet.write(2, col + 1, report_headers[col], format_1)
            #     row_header = 3
            #     col_header = 1
            #     for k, val in lines.items():
            #         sheet.write(row_header, 0, k, format_2)
            #         p_header = row_header + 1
            #         for rec in val['products']:
            #             sheet.write(p_header, 0, rec, format_1)
            #             p_header+=1
            #
            #         sheet.write(row_header, col_header, val['qty'], format_2)
            #
            #         sheet.write(row_header, col_header + 1, val['sales'], format_2)
            #         # sum_sale += val['sales']
            #         # sheet.write(row_header, col_header + 1, val['return'], format_1)
            #         # # sum_return += val['return']
            #         # sheet.write(row_header, col_header + 2, val['ach'], format_1)
            #         # sum_ach += val['ach']
            #         sheet.write(row_header, col_header + 2, val['sale_in_cost'], format_2)
            #         # sum_cost += val['sale_in_cost']
            #         sheet.write(row_header, col_header + 3, val['profit'], format_2)
            #         sheet.write(row_header, col_header + 4, val['onhand'], format_2)
            #
            #         sheet.write(row_header, col_header + 5, val['onhand_value'], format_2)
            #
            #         # sum_gain += val['gain']
            #         sheet.write(row_header, col_header + 6, round(val['gain_perc'], 2), format_2)
            #
            #         # sum_gain_perc += val['gain_perc']
            #         row_header = p_header+1
            # elif data['sorting'] == 'vendor_details':
            #
            #     for col in range(len(report_headers)-4):
            #         sheet.write(2, col + 1, report_headers[col], format_1)
            #     p_header = 3
            #
            #     col_header = 1
            #     for k, val in lines.items():
            #         for rec in val:
            #             for key,v in rec.items():
            #               sheet.write(p_header, 0, key, format_1)
            #               sheet.write(p_header, col_header, v['qty'], format_1)
            #               sheet.write(p_header, col_header + 1, v['sales'], format_1)
            #               sum_qty += v['qty']
            #               sum_sale += v['sales']
            #               sum_cost += v['sale_in_cost']
            #               sum_onhand += v['onhand']
            #               sum_profit += v['profit']
            #               sum_onhand_value += v['onhand_value']
            #
            #         # sheet.write(row_header, col_header + 1, val['return'], format_1)
            #         # # sum_return += val['return']
            #         # sheet.write(row_header, col_header + 2, val['ach'], format_1)
            #         # sum_ach += val['ach']
            #               sheet.write(p_header, col_header + 2, v['sale_in_cost'], format_1)
            #                 # sum_cost += val['sale_in_cost']
            #               sheet.write(p_header, col_header + 3, v['profit'], format_1)
            #               sheet.write(p_header, col_header + 4, v['onhand'], format_1)
            #
            #               sheet.write(p_header, col_header + 5, v['onhand_value'], format_1)
            #               sheet.write(p_header, col_header + 6, v['gain_perc'], format_1)
            #               p_header+=1
            #         sheet.write(p_header, 0,k, format_2)
            #         sheet.write(p_header,col_header ,sum_qty, format_2)
            #         sheet.write(p_header,col_header+1 ,sum_sale, format_2)
            #         sheet.write(p_header,col_header+2 ,sum_cost, format_2)
            #
            #         sheet.write(p_header,col_header+3 ,sum_profit, format_2)
            #         sheet.write(p_header,col_header+4 ,sum_onhand, format_2)
            #         sheet.write(p_header,col_header+5 ,sum_onhand_value, format_2)

        else:
            raise UserError(_("There is no Data available."))

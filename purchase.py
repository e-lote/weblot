# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import pytz
import math

from openerp import SUPERUSER_ID
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import fields, osv
from openerp import netsvc
from openerp import pooler
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.osv.orm import browse_record, browse_null
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

from openerp.addons.purchase.purchase import purchase_order as original_purchase_order


original_purchase_order.STATE_SELECTION.extend([
    ('consolidated', 'Consolidated'),
    ('not_valid',    'Not Valid'),
    ('in_process',   'In Process'),
    ('dispatched',   'Dispatched'),
    ('received',     'Received'),
])



class purchase_order(osv.osv):
	_name = 'purchase.order'
	_inherit = 'purchase.order'

        _track = {
            'state': {
                'purchase.mt_rfq_consolidated': lambda self, cr, uid, obj, ctx=None: obj.state == 'consolidated',
                'purchase.mt_rfq_in_process':   lambda self, cr, uid, obj, ctx=None: obj.state == 'in_process',
                'purchase.mt_rfq_dispatched':   lambda self, cr, uid, obj, ctx=None: obj.state == 'dispatched',
                'purchase.mt_rfq_received':     lambda self, cr, uid, obj, ctx=None: obj.state == 'received',
            }
        }

###############################################################################################################################
	def _fnct_po_total_volume(self, cr, uid, ids, field_name, args, context=None):
		if context is None:
			context = {}
		res = {}

                for obj in self.browse(cr,uid,ids,context=context):
                    total_volume = 0
                    for line in obj.order_line:
                            total_volume = total_volume + line.porc_teu
                    res[obj.id] = total_volume

		return res
###############################################################################################################################
	def _fnct_po_porc_teu1(self, cr, uid, ids, field_name, args, context=None):
		if context is None:
			context = {}
		res = {}

                for obj in self.browse(cr,uid,ids,context=context):
                    total_volume = obj.total_volume 
                    porc_teu = (1-(total_volume/30))*100
                    if porc_teu < 0:
                            res[obj.id] = -1
                    else:	
			res[obj.id] = (1-(total_volume/30))*100

		return res
###############################################################################################################################
	def _fnct_po_porc_teu2(self, cr, uid, ids, field_name, args, context=None):
		if context is None:
			context = {}
		res = {}

                for obj in self.browse(cr,uid,ids,context=context):
                    total_volume = obj.total_volume 
                    porc_teu = (1-(total_volume/60))*100
                    if porc_teu < 0:
                            res[obj.id] = -1
                    else:	
                            res[obj.id] = (1-(total_volume/60))*100

		return res
###############################################################################################################################
	def _fnct_po_total_weight(self, cr, uid, ids, field_name, args, context=None):
		if context is None:
			context = {}
		res = {}

                for obj in self.browse(cr,uid,ids,context=context):
                    total_weight = 0
                    for line in obj.order_line:
                            total_weight = total_weight + line.weight
                    res[obj.id] = total_weight

		return res

        #def write(self, cr, uid, ids, vals, context=None):
	#	if 'delivered' in vals.keys():
	#		vals['state'] = 'delivered'
	#	if 'in_transit' in vals.keys():
	#		vals['state'] = 'in_transit'
	#	if 'not_valid' in vals.keys():
	#		vals['state'] = 'not_valid'
        #	return super(purchase_order, self).write(cr, uid, ids, vals, context=context)

	_columns = {
		'sb_origin': fields.related('create_uid','partner_id',type="many2one",relation="res.partner",string="SB Origin",readonly=True),
                'total_volume': fields.function(_fnct_po_total_volume,string='Volume (m3)',type='float'),
                'porc_teu1': fields.function(_fnct_po_porc_teu1,string='Porc faltante 1 TEU',type='float'),
                'porc_teu2': fields.function(_fnct_po_porc_teu2,string='Porc faltante 2 TEUs',type='float'),
                'total_volume': fields.function(_fnct_po_total_volume,string='Volume (m3)',type='float'),
                'total_weight': fields.function(_fnct_po_total_weight,string='Weight (kg)',type='float'),
		'cashflow': fields.binary('Cashflow'),
                'state': fields.selection(original_purchase_order.STATE_SELECTION, 'Status', readonly=True,
                                          help="The status of the purchase order or the quotation request. "
                                               "A request for quotation is a purchase order in a 'Draft' status. "
                                               "Then the order has to be confirmed by the user, the status switch "
                                               "to 'Confirmed'. Then the supplier must confirm the order to change "
                                               "the status to 'Approved'. When the purchase order is paid and "
                                               "received, the status becomes 'Done'. If a cancel action occurs in "
                                               "the invoice or in the receipt of goods, the status becomes "
                                               "in exception.",
                                          select=True, copy=False),
		}

purchase_order()

class purchase_order_line(osv.osv):
    _name = 'purchase.order.line'
    _inherit = 'purchase.order.line'

    def write(self, cr, uid, ids, vals, context=None):
	if 'boxes' in vals:
		obj = self.browse(cr,uid,ids)
		order_id = obj[0].order_id.id
		if order_id:
			order = self.pool.get('purchase.order').browse(cr,uid,order_id)
			partner_id = order.partner_id.id

			product_supplier_id = self.pool.get('product.supplierinfo').search(cr,uid,\
				[('product_tmpl_id','=',obj[0].product_id.product_tmpl_id.id),('name','=',partner_id)])
			if product_supplier_id:
				product_supplier = self.pool.get('product.supplierinfo').browse(cr,uid,product_supplier_id)[0]			
				vals['price_unit'] = product_supplier.supplier_price
				vals['product_qty'] = product_supplier.carton_quantity * vals['boxes']
        if 'price_unit' in vals:
		obj = self.browse(cr,uid,ids)
		order_id = obj[0].order_id.id
		if order_id:
			order = self.pool.get('purchase.order').browse(cr,uid,order_id)
			partner_id = order.partner_id.id

			product_supplier_id = self.pool.get('product.supplierinfo').search(cr,uid,\
				[('product_tmpl_id','=',obj[0].product_id.product_tmpl_id.id),('name','=',partner_id)])
			if product_supplier_id:
				product_supplier = self.pool.get('product.supplierinfo').browse(cr,uid,product_supplier_id)[0]			
				vals['price_unit'] = product_supplier.supplier_price
				vals['product_qty'] = product_supplier.carton_quantity * vals['boxes']
    	return super(purchase_order_line, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
	# obj = self.browse(cr,uid,vals['order_id'])
	if vals['order_id']:
		order = self.pool.get('purchase.order').browse(cr,uid,vals['order_id'])
		partner_id = order.partner_id.id
		product_obj = self.pool.get('product.product').browse(cr,uid,vals['product_id'])

		product_supplier_id = self.pool.get('product.supplierinfo').search(cr,uid,\
			[('product_tmpl_id','=',product_obj.product_tmpl_id.id),('name','=',partner_id)])
		if product_supplier_id:
			product_supplier = self.pool.get('product.supplierinfo').browse(cr,uid,product_supplier_id)
			vals['price_unit'] = product_supplier[0].supplier_price
			vals['product_qty'] = product_supplier[0].carton_quantity * vals['boxes']
    	return super(purchase_order_line, self).create(cr, uid, vals, context=context)


    def _amount_line(self, cr, uid, ids, prop, arg, context=None):
	# import pdb;pdb.set_trace()
        res = {}
        cur_obj=self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            taxes = tax_obj.compute_all(cr, uid, line.taxes_id, line.price_unit, line.product_qty, line.product_id, line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])+line.additional_cost
        return res



    def _fnct_line_product_state(self, cr, uid, ids, field_name, args, context=None):

        if context is None:
            context = {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
		if not line.product_id.state:
        		res[line.id] = 'N/A'
		else:
	        	res[line.id] = line.product_id.state
        return res

    def _fnct_po_carton_volume(self, cr, uid, ids, field_name, args, context=None):
	if context is None:
		context = {}
	res = {}
	for line in self.browse(cr, uid, ids, context=context):
		product_id = line.product_id.id
		product_tmpl_id = line.product_id.product_tmpl_id.id
		order = self.pool.get('purchase.order').browse(cr,uid,line.order_id.id)
		partner_id = order.partner_id.id
		supplier_id = self.pool.get('product.supplierinfo').search(cr,uid,[('name','=',partner_id),\
					('product_tmpl_id','=',product_tmpl_id)])
		supplier = self.pool.get('product.supplierinfo').browse(cr,uid,supplier_id)[0] if supplier_id else False
		res[line.id] = supplier.carton_volume if supplier and supplier.carton_quantity > 0 else False

	return res
###############################################################################################################################
# ADDITIONAL COSTS
###############################################################################################################################
    def _fnct_po_additional_cost(self, cr, uid, ids, field_name, args, context=None):
	if context is None:
		context = {}
	res = {}
	for line in self.browse(cr, uid, ids, context=context):
		product_id = line.product_id.id
		product_tmpl_id = line.product_id.product_tmpl_id.id
		order = self.pool.get('purchase.order').browse(cr,uid,line.order_id.id)
		partner_id = order.partner_id.id
		supplier_id = self.pool.get('product.supplierinfo').search(cr,uid,[('name','=',partner_id),\
					('product_tmpl_id','=',product_tmpl_id)])
		# import pdb;pdb.set_trace()
		supplier = self.pool.get('product.supplierinfo').browse(cr,uid,supplier_id)[0] if supplier_id else False
		res[line.id] = line.product_qty * ( supplier.developing_cost + supplier.royalties + \
				(supplier.supplier_price * supplier.service_fee/100 )) if supplier and supplier.service_fee > 0 else False
	return res
###############################################################################################################################
# 
###############################################################################################################################
    def _fnct_po_carton_quantity(self, cr, uid, ids, field_name, args, context=None):
	if context is None:
		context = {}
	res = {}
	for line in self.browse(cr, uid, ids, context=context):
		product_id = line.product_id.id
		product_tmpl_id = line.product_id.product_tmpl_id.id
		order = self.pool.get('purchase.order').browse(cr,uid,line.order_id.id)
                try:
		    partner_id = order.partner_id.id
		    supplier_id = self.pool.get('product.supplierinfo').search(cr,uid,[('name','=',partner_id),\
		    			('product_tmpl_id','=',product_tmpl_id)])
		    supplier = self.pool.get('product.supplierinfo').browse(cr,uid,supplier_id)[0] if supplier_id else False
		    res[line.id] = supplier.carton_quantity if supplier and supplier.carton_quantity > 0 else False
                except:
		    res[line.id] = False
	return res



###################################################################################################################################
    def _fnct_po_porc_teu(self, cr, uid, ids, field_name, args, context=None):
	if context is None:
		context = {}
	res = {}
	for line in self.browse(cr, uid, ids, context=context):
		product_id = line.product_id.id
		product_tmpl_id = line.product_id.product_tmpl_id.id
		order = self.pool.get('purchase.order').browse(cr,uid,line.order_id.id)
		partner_id = order.partner_id.id
		supplier_id = self.pool.get('product.supplierinfo').search(cr,uid,[('name','=',partner_id),\
					('product_tmpl_id','=',product_tmpl_id)])
		supplier = self.pool.get('product.supplierinfo').browse(cr,uid,supplier_id)[0] if supplier_id else False
		res[line.id] = line.boxes * supplier.carton_volume if supplier and supplier.carton_quantity > 0 else False

	return res
###################################################################################################################################
    def _fnct_pol_weight(self, cr, uid, ids, field_name, args, context=None):
	if context is None:
		context = {}
	res = {}
	for line in self.browse(cr, uid, ids, context=context):
		product_id = line.product_id.id
		product_tmpl_id = line.product_id.product_tmpl_id.id
		order = self.pool.get('purchase.order').browse(cr,uid,line.order_id.id)
		partner_id = order.partner_id.id
		supplier_id = self.pool.get('product.supplierinfo').search(cr,uid,[('name','=',partner_id),\
					('product_tmpl_id','=',product_tmpl_id)])
		supplier = self.pool.get('product.supplierinfo').browse(cr,uid,supplier_id)[0] if supplier_id else False
		res[line.id] = line.boxes * supplier.carton_weight if supplier and supplier.carton_weight > 0 else False

	return res

    def _fnct_sb_origin(self, cr, uid, ids, field_name, args, context=None):
        	if context is None:
                	context = {}
	        res = {}
        	for line in self.browse(cr, uid, ids, context=context):
			res[line.id] = line.order_id.sb_origin.id if line.order_id.sb_origin else False

	        return res

    def _fnct_cp(self, cr, uid, ids, field_name, args, context=None):
        	if context is None:
                	context = {}
	        res = {}
        	for line in self.browse(cr, uid, ids, context=context):
        	        res[line.id] = line.order_id.partner_id.id if line.order_id.partner_id else False

	        return res



    _columns = {
	        'sb_origin': fields.function(_fnct_sb_origin, string='SB Origin'),
	        'production_center': fields.function(_fnct_cp, string='Production Center'),
		'boxes': fields.integer('Boxes',required=True),
		'isbn': fields.related('product_id','ean13',type="char",string="ISBN",readonly=True),
	        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
		'product_state': fields.function(_fnct_line_product_state, string='Product State',type='char'),
                'carton_quantity': fields.function(_fnct_po_carton_quantity,string='Carton Quantity',type='float'),
                'carton_volume': fields.function(_fnct_po_carton_volume,string='Carton Volume',type='float'),
                'porc_teu': fields.function(_fnct_po_porc_teu,string='% TEU',type='float'),
                'weight': fields.function(_fnct_pol_weight,string='Weight',type='float'),
                # 'service_fee': fields.function(_fnct_po_service_fee,string='Service Fee',type='float'),
                # 'royalties': fields.function(_fnct_po_service_fee,string='Royalties',type='float'),
                # 'developing_cost': fields.function(_fnct_po_developing_cost,string='Developing Cost',type='float'),
                'additional_cost': fields.function(_fnct_po_additional_cost,string='Additional Cost',type='float'),
	        # 'price_unit': fields.float('Unit Price', required=True, readonly=True, digits_compute= dp.get_precision('Product Price')),
	}

    _defaults = {
	'boxes': 0,
	}


    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft', context=None):

        
        # onchange handler of product_id.
        if context is None:
            context = {}

        res = {'value': {'price_unit': price_unit or 0.0, 'name': name or '', 'product_uom' : uom_id or False}}
        if not product_id:
            return res

        product_product = self.pool.get('product.product')
        product_uom = self.pool.get('product.uom')
        res_partner = self.pool.get('res.partner')
        product_supplierinfo = self.pool.get('product.supplierinfo')
        product_pricelist = self.pool.get('product.pricelist')
        account_fiscal_position = self.pool.get('account.fiscal.position')
        account_tax = self.pool.get('account.tax')

        # - check for the presence of partner_id and pricelist_id
        if not partner_id:
            raise osv.except_osv(_('No Partner!'), _('Select a partner in purchase order to choose a product.'))
        #if not pricelist_id:
        #    raise osv.except_osv(_('No Pricelist !'), _('Select a price list in the purchase order form before choosing a product.'))

        # - determine name and notes based on product in partner lang.
        context_partner = context.copy()
        if partner_id:
            lang = res_partner.browse(cr, uid, partner_id).lang
            context_partner.update( {'lang': lang, 'partner_id': partner_id} )
        product = product_product.browse(cr, uid, product_id, context=context_partner)
        #call name_get() with partner in the context to eventually match name and description in the seller_ids field
        dummy, name = product_product.name_get(cr, uid, product_id, context=context_partner)[0]
        if product.description_purchase:
            name += '\n' + product.description_purchase
        res['value'].update({'name': name})

        # - set a domain on product_uom
        res['domain'] = {'product_uom': [('category_id','=',product.uom_id.category_id.id)]}

        # - check that uom and product uom belong to the same category
        product_uom_po_id = product.uom_po_id.id
        if not uom_id:
            uom_id = product_uom_po_id

        if product.uom_id.category_id.id != product_uom.browse(cr, uid, uom_id, context=context).category_id.id:
            if context.get('purchase_uom_check') and self._check_product_uom_group(cr, uid, context=context):
                res['warning'] = {'title': _('Warning!'), 'message': _('Selected Unit of Measure does not belong to the same category as the product Unit of Measure.')}
            uom_id = product_uom_po_id

        res['value'].update({'product_uom': uom_id})

        # - determine product_qty and date_planned based on seller info
        if not date_order:
            date_order = fields.date.context_today(self,cr,uid,context=context)


        supplierinfo = False
        supplier_price = 0
	if not product.seller_ids or \
		not product_supplierinfo.search(cr,uid,[('name','=',partner_id),('product_tmpl_id','=',product.product_tmpl_id.id)]):
        	raise osv.except_osv(_('No Supplier  Info !'), _('Product has no supplier information.'))
	

        supplierinfo = False
        for supplier in product.seller_ids:
	    # import pdb;pdb.set_trace()
  	    supplier_price = supplier.supplier_price
            if partner_id and (supplier.name.id == partner_id):
                supplierinfo = supplier
		supplier_price = supplierinfo.supplier_price
                if supplierinfo.product_uom.id != uom_id:
                    res['warning'] = {'title': _('Warning!'), 'message': _('The selected supplier only sells this product by %s') % supplierinfo.product_uom.name }
                min_qty = product_uom._compute_qty(cr, uid, supplierinfo.product_uom.id, supplierinfo.min_qty, to_uom_id=uom_id)
                if (qty or 0.0) < min_qty: # If the supplier quantity is greater than entered from user, set minimal.
                    if qty:
                        res['warning'] = {'title': _('Warning!'), 'message': _('The selected supplier has a minimal quantity set to %s %s, you should not purchase less.') % (supplierinfo.min_qty, supplierinfo.product_uom.name)}
                    qty = min_qty
        dt = self._get_date_planned(cr, uid, supplierinfo, date_order, context=context).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        qty = qty or 1.0
        res['value'].update({'date_planned': date_planned or dt})
        if qty:
            res['value'].update({'product_qty': qty})

        # - determine price_unit and taxes_id
	# import pdb;pdb.set_trace()
        if state not in ('sent','bid') and supplierinfo.supplier_price:
        	if pricelist_id:
		    price = product_pricelist.price_get(cr, uid, [pricelist_id],
                	    product.id, qty or 1.0, partner_id or False, {'uom': uom_id, 'date': date_order})[pricelist_id]
		    price = supplierinfo.supplier_price
	        else:
            # price = product.standard_price
		    price = supplierinfo.supplier_price
	else:
	    price = supplierinfo.supplier_price or 0

        taxes = account_tax.browse(cr, uid, map(lambda x: x.id, product.supplier_taxes_id))
        fpos = fiscal_position_id and account_fiscal_position.browse(cr, uid, fiscal_position_id, context=context) or False
        taxes_ids = account_fiscal_position.map_tax(cr, uid, fpos, taxes)
        res['value'].update({'price_unit': price, 'taxes_id': taxes_ids,'isbn': product.ean13})
	# import pdb;pdb.set_trace()

        return res


purchase_order_line()

class purchase_order_exceptions(osv.osv):
        _name = 'purchase.order.exception'
        _description = 'Exceptions to POs'

        _columns = {
                'order_id': fields.many2one('purchase.order','Pedido'),
                'product_id': fields.many2one('product.product','Producto'),
                'reason': fields.selection((('1','No llega al mínimo de producción'),('2','Otros motivos')),'Razón de rechazo'),
                'qty': fields.integer('Quantity'),
                }

purchase_order_exceptions()



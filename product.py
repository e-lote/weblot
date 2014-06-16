# -*- coding: utf-8 -*-

from openerp.osv import osv,fields

class product_supplierinfo(osv.osv):
	_name = "product.supplierinfo"
	_inherit = "product.supplierinfo"

	_columns = {
		'supplier_price': fields.float('Supplier Price'),
		'minimum_production': fields.float('Minimum Production'),
		'stocking_status': fields.selection((('Make & Hold','Make & Hold'),('On Demand','On Demand')),'Stocking Status'),
		'service_fee': fields.float('Service Fee'),
		'developing_cost': fields.float('Developing Cost'),
		'royalties': fields.float('Royalties'),
		'carton_quantity': fields.float('Carton Quantity'),
		'carton_weight': fields.float('Carton Weight'),
		'carton_width': fields.float('Carton Width'),
		'carton_length': fields.float('Carton Length'),
		'carton_heigth': fields.float('Carton Heigth'),
		'carton_volume': fields.float('Carton Volume'),
		'porc_teu': fields.float('% TEU'),
		}
       
product_supplierinfo()

"""
class product_packaging(osv.osv):
	_name = 'product.packaging'
	_inherit = 'product.packaging'

	_columns = {
		porc_teu: fields.float('% TEU'),
		}

	def _check_percent(self, cr, uid, ids, context=None):
		obj = self.browse(cr, uid, ids[0], context=context)
		if ( obj.porc_teu < 0.0 or obj.porc_teu > 100.0):
			return False
		return True

	_constraints = [
        	(_check_percent, 'Percentages for  between 0 and 100.', ['porc_teu']),
	]


product_product()
"""

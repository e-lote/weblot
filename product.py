# -*- coding: utf-8 -*-

from openerp.osv import osv,fields

class product_supplierinfo(osv.osv):
	_name = "product.supplierinfo"
	_inherit = "product.supplierinfo"

	def _fnct_default_code(self, cr, uid, ids, field_name, args, context=None):
        	if context is None:
                	context = {}
	        res = {}
		product = self.pool.get('product.product')
        	for line in self.browse(cr, uid, ids, context=context):
	                product_id = product.search(cr,uid,[('product_tmpl_id','=',line.id)])
			product_obj = product.browse(cr,uid,product_id)
                	if product_obj:
        	                res[line.id] = product_obj[0].default_code
                	else:
                        	res[line.id] = ''

	        return res

	def _fnct_search_default_code(self, cursor, user, obj, name, args, context=None):
        	if not len(args):
	            return []
        	for arg in args:
			if arg[0] == 'default_code':
				condicion = arg[1]
				argumento = "'" + arg[2] + "'"

	        cursor.execute("SELECT a.id FROM product_product a "+ \
                	"WHERE a.default_code " + condicion + " " + argumento)
	        res = cursor.fetchall()
		res.extend(cursor.fetchall())
	        if not res:
        	    return [('id', '=', 0)]
	        return [('id', 'in', [x[0] for x in res])]

	def _fnct_isbn(self, cr, uid, ids, field_name, args, context=None):
        	if context is None:
                	context = {}
	        res = {}
		product = self.pool.get('product.product')
        	for line in self.browse(cr, uid, ids, context=context):
	                product_id = product.search(cr,uid,[('product_tmpl_id','=',line.product_tmpl_id.id)])
			product_obj = product.browse(cr,uid,product_id)
                	if product_obj:
        	                res[line.id] = product_obj[0].ean13
                	else:
                        	res[line.id] = ''

	        return res

	def _fnct_search_isbn(self, cursor, user, obj, name, args, context=None):
        	if not len(args):
	            return []
        	for arg in args:
			if arg[0] == 'isbn':
				condicion = arg[1]
				argumento = "'" + arg[2] + "'"

	        cursor.execute("SELECT a.id FROM product_product a "+ \
                	"WHERE a.ean13 " + condicion + " " + argumento)
	        res = cursor.fetchall()
		res.extend(cursor.fetchall())
	        if not res:
        	    return [('id', '=', 0)]
	        return [('id', 'in', [x[0] for x in res])]

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
		'isbn': fields.function(_fnct_isbn,string='ISBN',type='char',fnct_search=_fnct_search_isbn),
		'default_code': fields.function(_fnct_default_code,string='Default Code',type='char',fnct_search=_fnct_search_default_code),
		}
       
product_supplierinfo()


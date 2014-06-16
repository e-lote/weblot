from openerp.osv import osv,fields
import string

class res_partner(osv.osv):
	_name = "res.partner"
	_inherit = "res.partner"

        def _check_phones(self, cr, uid, ids, context=None):
            obj = self.browse(cr, uid, ids[0], context=context)
            if (not obj.phone) and (not obj.mobile):
                return False
            return True

        def _check_null_values(self, cr, uid, ids, context=None):
            obj = self.browse(cr, uid, ids[0], context=context)
            if (not obj.name) or (not obj.city) or (not obj.street) or (not obj.user_id) or (not obj.zip) or (not obj.email):
                return False
            return True


        def _update_warning_msgs(self,cr,uid,ids=None,context=None):
	    partner_ids = self.search(cr,uid,[('credit','>',0)])
	    for partner in self.browse(cr,uid,partner_ids):
	        val_warn_msg = {
			'sale_warn_msg': 'El cliente cuenta con una deuda de '+str(partner.credit)+' $',
			'sale_warn': 'warning',
			'invoice_warn_msg': 'El cliente cuenta con una deuda de '+str(partner.credit)+' $',
			'invoice_warn': 'warning',
			}
		return_id = self.write(cr,uid,partner.id,val_warn_msg)
	    return True


        _constraints = [
		(_check_null_values, 'Nombre, calle, ciudad, codigo postal, email y promotor\nson campos que no pueden ser nulos',['name','city','street','user_id','zip','email']),
		(_check_phones, 'Se debe ingresar el telefono o celular',['phone','mobile']),
		]

	_columns = {
		'cod_epicor': fields.char('Codigo EPICOR',size=10),
		'region': fields.char('Region',size=3),
		'sucursal': fields.char('Sucursal',size=1),
		'canal': fields.char('Canal',size=4),
	        'user_id': fields.many2one('res.users', 'Promotor', help='The internal user that is in charge of communicating with this contact if any.'),
		}
       
        def write(self, cr, uid, ids, vals, context=None):
            if 'name' in vals:
		if vals['name']:
		        vals['name'] = vals['name'].upper()
            if 'street' in vals:
		if vals['street']:
		        vals['street'] = vals['street'].upper()
            if 'city' in vals:
		if vals['city']:
		        vals['city'] = vals['city'].upper()
            return super(res_partner, self).write(cr, uid, ids, vals, context=context)

        def create(self, cr, uid, vals, context=None):
            if 'name' in vals:
		if vals['name']:
		        vals['name'] = vals['name'].upper()
            if 'street' in vals:
		if vals['street']:
		        vals['street'] = vals['street'].upper()
            if 'city' in vals:
		if vals['city']:
		        vals['city'] = vals['city'].upper()
            return super(res_partner, self).create(cr, uid, vals, context=context)

	
res_partner()

# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp

from openerp.addons.purchase.purchase import purchase_order \
    as original_purchase_order

original_purchase_order.STATE_SELECTION.extend([
    ('consolidated', 'Consolidated'),
    ('not_valid',    'Not Valid'),
    ('in_process',   'In Process'),
    ('dispatched',   'Dispatched'),
    ('received',     'Received'),
])

writeable_on_draft = {
    'confirmed':    [('readonly', True)],
    'approved':     [('readonly', True)],
    'consolidated': [('readonly', True)],
    'not_valid':    [('readonly', True)],
    'in_process':   [('readonly', True)],
    'dispatched':   [('readonly', True)],
    'received':     [('readonly', True)]
}

state_help = """
The status of the purchase order or the quotation request.
A request for quotation is a purchase order in a 'Draft' status.
Then the order has to be confirmed by the user, the status switch
to 'Confirmed'. Then the supplier must confirm the order to change
the status to 'Approved'. When the purchase order is paid and
received, the status becomes 'Done'. If a cancel action occurs in
the invoice or in the receipt of goods, the status becomes
in exception.
"""


class purchase_order(osv.osv):
    _name = 'purchase.order'
    _inherit = 'purchase.order'

    _track = {
        'state': {
            'purchase.mt_rfq_consolidated':
                lambda self, cr, uid, obj, ctx=None:
                    obj.state == 'consolidated',
            'purchase.mt_rfq_in_process':
                lambda self, cr, uid, obj, ctx=None: obj.state == 'in_process',
            'purchase.mt_rfq_dispatched':
                lambda self, cr, uid, obj, ctx=None: obj.state == 'dispatched',
            'purchase.mt_rfq_received':
                lambda self, cr, uid, obj, ctx=None: obj.state == 'received',
        }
    }

    def _fnct_po_total_volume(self, cr, uid, ids, field_name, args,
                              context=None):
        if context is None:
            context = {}
        res = {}
        for obj in self.browse(cr, uid, ids, context=context):
            total_volume = 0
            for line in obj.order_line:
                total_volume = total_volume + line.porc_teu
            res[obj.id] = total_volume
        return res

    def _fnct_po_porc_teu1(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
        res = {}

        for obj in self.browse(cr, uid, ids, context=context):
            total_volume = obj.total_volume
            porc_teu = (1-(total_volume/30))*100
            if porc_teu < 0:
                res[obj.id] = -1
            else:
                res[obj.id] = (1-(total_volume/30))*100

        return res

    def _fnct_po_porc_teu2(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
        res = {}

        for obj in self.browse(cr, uid, ids, context=context):
            total_volume = obj.total_volume
            porc_teu = (1-(total_volume/60))*100
            if porc_teu < 0:
                res[obj.id] = -1
            else:
                res[obj.id] = (1-(total_volume/60))*100

        return res

    def _fnct_po_total_weight(self, cr, uid, ids, field_name, args,
                              context=None):
        if context is None:
            context = {}
        res = {}

        for obj in self.browse(cr, uid, ids, context=context):
            total_weight = 0
            for line in obj.order_line:
                total_weight = total_weight + line.weight
            res[obj.id] = total_weight

        return res

    def _fnct_po_is_managed(self, cr, uid, ids, field_name, args, context=None):
        user_obj = self.pool.get('res.users')
        if context is None:
            context = {}
        res = {}

        for obj in self.browse(cr, uid, ids, context=context):
            res[obj.id] = (not obj.responsible_id) or \
                (obj.responsible_id and uid == obj.responsible_id.id) or \
                (user_obj.has_group(cr, uid,
                                    'weblot.group_elote_manager_purchaser'))

        return res

    _columns = {
        'sb_origin': fields.many2one('res.partner', string="SB Origin",
                                     required=True,
                                     states=writeable_on_draft),
        'responsible_id': fields.many2one('res.users', string="Responsible",
                                          required=True,
                                          states=writeable_on_draft),
        'total_volume': fields.function(_fnct_po_total_volume,
                                        string='Volume (m3)', type='float'),
        'porc_teu1': fields.function(_fnct_po_porc_teu1,
                                     string='Porc faltante 1 TEU',
                                     type='float'),
        'porc_teu2': fields.function(_fnct_po_porc_teu2,
                                     string='Porc faltante 2 TEUs',
                                     type='float'),
        'total_volume': fields.function(_fnct_po_total_volume,
                                        string='Volume (m3)',
                                        type='float'),
        'total_weight': fields.function(_fnct_po_total_weight,
                                        string='Weight (kg)',
                                        type='float'),
        'is_managed': fields.function(_fnct_po_is_managed,
                                      string='Is managed',
                                      type='boolean'),
        'cashflow': fields.binary('Cashflow', states=writeable_on_draft),
        'state': fields.selection(original_purchase_order.STATE_SELECTION,
                                  'Status',
                                  readonly=True,
                                  help=state_help,
                                  select=True, copy=False),
    }

    _defaults = {
        'responsible_id': lambda self, cr, uid, *args: uid,
        'sb_origin':
            lambda self, cr, uid, *args:
        self.pool.get('res.users').browse(cr, uid, uid).partner_id.parent_id.id
    }

purchase_order()


class purchase_order_line(osv.osv):
    _name = 'purchase.order.line'
    _inherit = 'purchase.order.line'

    def _fnct_product_qty(self, cr, uid, ids, field, arg, context=None):
        """
        Compute product quantity
        """
        if context is None:
            context = {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            supplierinfo = line.supplierinfo_id
            res[line.id] = supplierinfo.carton_quantity * line.boxes
        return res

    def _fnct_amount_line(self, cr, uid, ids, field, arg, context=None):
        """
        Compute price subtotal
        """
        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            taxes = tax_obj.compute_all(cr, uid, line.taxes_id, line.price_unit,
                                        line.product_qty, line.product_id,
                                        line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = (cur_obj.round(cr, uid, cur, taxes['total']) +
                            line.additional_cost)
        return res

    def _fnct_unit_cost(self, cr, uid, ids, field, arg, context=None):
        """
        Compute price unit
        """
        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            taxes = tax_obj.compute_all(cr, uid, line.taxes_id, line.price_unit,
                                        1, line.product_id,
                                        line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = (cur_obj.round(cr, uid, cur, taxes['total']) +
                            line.unit_additional_cost)
        return res

    def _fnct_po_unit_additional_cost(self, cr, uid, ids, field, args,
                                      context=None):
        """
        Compute Additional Cost for Unit
        """
        if context is None:
            context = {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            supplier = line.supplierinfo_id
            res[line.id] = (
                supplier.developing_cost + supplier.royalties +
                (supplier.supplier_price * supplier.service_fee/100)) \
                if supplier and supplier.service_fee > 0 else False
        return res

    def _fnct_po_additional_cost(self, cr, uid, ids, field, args, context=None):
        """
        Compute Additional Cost
        """
        if context is None:
            context = {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            supplier = line.supplierinfo_id
            res[line.id] = line.product_qty * (
                supplier.developing_cost + supplier.royalties +
                (supplier.supplier_price * supplier.service_fee/100)
            ) if supplier and supplier.service_fee > 0 else False
        return res

    def _fnct_po_porc_teu(self, cr, uid, ids, field, args, context=None):
        """
        Compute TEU
        """
        if context is None:
            context = {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            supplier = line.supplierinfo_id
            res[line.id] = line.boxes * supplier.carton_volume \
                if supplier and supplier.carton_quantity > 0 else False

        return res

    def _fnct_po_weight(self, cr, uid, ids, field, args, context=None):
        """
        Compute total Weight
        """
        if context is None:
            context = {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            supplier = line.supplierinfo_id
            res[line.id] = line.boxes * supplier.carton_weight \
                if supplier and supplier.carton_weight > 0 else False

        return res

    def _fnct_supplierinfo_id(self, cr, uid, ids, field, args, context=None):
        """
        Compute the supplierinfo
        """
        supplierinfo_obj = self.pool.get('product.supplierinfo')
        context = context or {}
        ret = {line.id: (supplierinfo_obj.search(cr, uid, [
            ('name', '=', line.order_id.partner_id.id),
            ('lote_id', '=', line.order_id.lote_id.id),
            ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)]
        ) + [False])[0] for line in self.browse(cr, uid, ids, context=context)}
        return ret

    _columns = {
        'supplierinfo_id': fields.function(_fnct_supplierinfo_id,
                                           type="many2one",
                                           relation='product.supplierinfo',
                                           string='Supplier info'),
        'boxes': fields.integer('Boxes', required=True),
        'isbn': fields.related(
            'product_id', 'ean13', type="char", string="ISBN", readonly=True),
        'price_subtotal': fields.function(
            _fnct_amount_line, string='Subtotal', type='float',
            digits_compute=dp.get_precision('Account')),
        'product_state': fields.related(
            'product_id', 'state',
            string='Product State', type='char'),
        'carton_quantity': fields.related(
            'supplierinfo_id', 'carton_quantity',
            string='Carton Quantity', type='float'),
        'carton_volume': fields.related(
            'supplierinfo_id', 'carton_volume',
            string='Carton Volume', type='float'),
        'porc_teu': fields.function(
            _fnct_po_porc_teu, string='% TEU', type='float'),
        'weight': fields.function(
            _fnct_po_weight, string='Weight', type='float'),
        'additional_cost': fields.function(
            _fnct_po_additional_cost, string='Additional Cost', type='float'),
        'unit_additional_cost': fields.function(
            _fnct_po_unit_additional_cost,
            string='Unit Additional Cost', type='float'),
        'unit_cost': fields.function(
            _fnct_unit_cost, string='Unit Additional Cost', type='float'),
        'price_unit': fields.related(
            'supplierinfo_id', 'supplier_price', type='float',
            string='Unit Price'),
        'product_qty': fields.function(
            _fnct_product_qty, string='Quantity', type='float'),
    }

    _defaults = {
        'boxes': 0,
    }

purchase_order_line()


class purchase_order_exceptions(osv.osv):
        _name = 'purchase.order.exception'
        _description = 'Exceptions to POs'

        _columns = {
            'order_id': fields.many2one('purchase.order', 'Pedido'),
            'product_id': fields.many2one('product.product', 'Producto'),
            'reason': fields.selection((
                ('1', 'No llega al mínimo de producción'),
                ('2', 'Otros motivos')
            ), 'Razón de rechazo'),
            'qty': fields.integer('Quantity'),
        }

purchase_order_exceptions()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

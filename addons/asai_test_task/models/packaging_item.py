from odoo import models, fields, api, _

class PackagingItem(models.Model):
    _name = 'packaging.item'
    _description = 'Packaging Item'
    _rec_name = 'item_code'

    order_id = fields.Many2one('packaging.order', string='Order', required=True, ondelete='cascade')
    product_name = fields.Char(string='Product Name', required=True)
    dimensions = fields.Char(string='Dimensions')
    item_code = fields.Char(string='Item ID', required=True)
    is_packed = fields.Boolean(string='Packed', default=False)
    pack_date = fields.Datetime(string='Pack Date')
    
    # Добавляем поле для брака
    is_defective = fields.Boolean(string='Defective', default=False)
    defective_reason = fields.Text(string='Defective Reason')
    defective_date = fields.Datetime(string='Defective Date')
    defective_operator_id = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user)

    def action_mark_as_packed(self):
        self.write({
            'is_packed': True,
            'pack_date': fields.Datetime.now()
        })

    def action_mark_as_unpacked(self):
        self.write({
            'is_packed': False,
            'pack_date': False
        })
    
    def action_mark_defective_simple(self):
        """Simple method to mark item as defective"""
        self.ensure_one()
        
        self.write({
            'is_defective': True,
            'defective_reason': 'Marked as defective by operator',
            'defective_date': fields.Datetime.now(),
            'defective_operator_id': self.env.user.id
        })
        
        # Принудительно обновляем статус заказа
        self.order_id._compute_packed_items()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Item Marked as Defective"),
                'message': _("Item %s has been marked as defective. Order status updated.") % self.item_code,
                'type': 'warning',
                'sticky': False,
            }
        }
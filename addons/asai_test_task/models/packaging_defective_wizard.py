from odoo import models, fields, api
from odoo.exceptions import UserError

class PackagingItemDefectiveWizard(models.TransientModel):
    _name = 'packaging.item.defective.wizard'
    _description = 'Mark Item as Defective'

    item_id = fields.Many2one('packaging.item', string='Item', required=True)
    defective_reason = fields.Text(string='Defective Reason', required=True, help='Please specify why this item is defective')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self._context.get('default_item_id'):
            res['item_id'] = self._context['default_item_id']
        return res

    def action_confirm_defective(self):
        """Confirm marking item as defective"""
        self.ensure_one()
        
        if not self.defective_reason:
            raise UserError("Please provide a reason for marking this item as defective!")
        
        # Помечаем товар как бракованный
        self.item_id.write({
            'is_defective': True,
            'defective_reason': self.defective_reason,
            'defective_date': fields.Datetime.now(),
            'defective_operator_id': self.env.user.id
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'packaging.order',
            'res_id': self.item_id.order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
from odoo import models, fields, api
from odoo.exceptions import UserError

class PackagingOrderDefectiveWizard(models.TransientModel):
    _name = 'packaging.order.defective.wizard'
    _description = 'Mark Order as Defective'

    order_id = fields.Many2one('packaging.order', string='Order', required=True)
    defective_reason = fields.Text(string='Defective Reason', required=True, help='Please specify why this order cannot be completed')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self._context.get('active_id'):
            res['order_id'] = self._context['active_id']
        return res

    def action_confirm_defective(self):
        """Confirm marking order as defective"""
        self.ensure_one()
        
        if not self.defective_reason:
            raise UserError("Please provide a reason for marking this order as defective!")
        
        # Обновляем заказ
        self.order_id.write({
            'state': 'defective',
            'defective_reason': self.defective_reason,
            'defective_date': fields.Datetime.now(),
            'defective_operator_id': self.env.user.id
        })
        
        # Закрываем wizard и возвращаемся к заказу
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'packaging.order',
            'res_id': self.order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
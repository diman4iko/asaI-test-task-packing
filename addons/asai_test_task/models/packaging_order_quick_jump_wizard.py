from odoo import models, fields, api
from odoo.exceptions import UserError


class PackagingOrderQuickJumpWizard(models.TransientModel):
    _name = 'packaging.order.quick.jump.wizard'
    _description = 'Quick Jump to Order Wizard'

    order_number = fields.Char(string='Order Number', required=True)

    def action_confirm_jump(self):
        """Jump to specified order"""
        self.ensure_one()

        if not self.order_number:
            raise UserError("Please enter an order number")

        # Ищем заказ по номеру
        order = self.env['packaging.order'].search([
            ('name', '=', self.order_number.strip())
        ], limit=1)

        if not order:
            raise UserError(f"Order with number {self.order_number} not found!")

        # Закрываем wizard и открываем заказ
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'packaging.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
            'views': [(False, 'form')],
        }
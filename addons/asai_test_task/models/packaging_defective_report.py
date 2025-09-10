from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class PackagingDefectiveReport(models.TransientModel):
    _name = 'packaging.defective.report'
    _description = 'Defective Orders Report'

    date_from = fields.Date(string='From Date', default=fields.Date.today() - timedelta(days=30))
    date_to = fields.Date(string='To Date', default=fields.Date.today())
    responsible_id = fields.Many2one('res.users', string='Responsible')
    show_details = fields.Boolean(string='Show Item Details', default=True)

    def action_generate_report(self):
        """Generate defective orders report"""
        self.ensure_one()
        
        domain = [
            ('state', '=', 'defective'),
            ('defective_date', '>=', self.date_from),
            ('defective_date', '<=', self.date_to)
        ]
        
        if self.responsible_id:
            domain.append(('responsible_id', '=', self.responsible_id.id))
        
        orders = self.env['packaging.order'].search(domain)
        
        if not orders:
            raise UserError(_("No defective orders found for selected period"))
        
        # Формируем данные отчета
        report_data = []
        for order in orders:
            defective_items = order.item_ids.filtered(lambda x: x.is_defective)
            order_data = {
                'order_number': order.name,
                'responsible': order.responsible_id.name,
                'defective_date': order.defective_date.strftime('%Y-%m-%d %H:%M:%S') if order.defective_date else '',
                'defective_reason': order.defective_reason or '',
                'reported_by': order.defective_operator_id.name,
                'total_items': order.total_items,
                'defective_items_count': len(defective_items),
                'defective_items': []
            }
            
            if self.show_details:
                for item in defective_items:
                    order_data['defective_items'].append({
                        'item_code': item.item_code,
                        'product_name': item.product_name,
                        'defective_reason': item.defective_reason or '',
                        'reported_by': item.defective_operator_id.name,
                        'defective_date': item.defective_date.strftime('%Y-%m-%d %H:%M:%S') if item.defective_date else ''
                    })
            
            report_data.append(order_data)
        
        # Создаем wizard для отображения результатов
        wizard = self.env['packaging.defective.report.wizard'].create({
            'report_data': str(report_data),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'responsible_id': self.responsible_id.id,
            'show_details': self.show_details
        })
        
        # Открываем wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _('Defective Orders Report'),
            'res_model': 'packaging.defective.report.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'view_id': self.env.ref('asai_test_task.view_defective_report_results_form').id,
            'target': 'new',
        }
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import re

_logger = logging.getLogger(__name__)

class PackagingLabel(models.Model):
    _name = 'packaging.label'
    _description = 'Packaging Label'
    _order = 'create_date desc'

    name = fields.Char(string='Label Number', required=True, default='New')
    order_id = fields.Many2one(
        'packaging.order', 
        string='Order', 
        required=True,
        ondelete='cascade'
    )
    label_data = fields.Binary(string='Label PDF', attachment=True)
    label_filename = fields.Char(string='Filename')
    print_date = fields.Datetime(string='Print Date', default=fields.Datetime.now)
    printed = fields.Boolean(string='Printed', default=False)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            # Используем последовательность вместо ручной генерации
            vals['name'] = self.env['ir.sequence'].next_by_code('packaging.label') or 'New'
        
        # Проверяем формат номера перед созданием
        if not re.match(r'^L\d+$', vals['name']):
            raise ValidationError(_("Label number must be in format L000001!"))
        
        if not vals.get('order_id'):
            raise UserError(_("Order ID is required for creating a label!"))
        
        # Создаем запись
        label = super(PackagingLabel, self).create(vals)
        
        # Генерируем PDF после создания
        label._generate_pdf_label()
            
        return label
    
    @api.constrains('name')
    def _check_label_number(self):
        """Validate that label number is in correct format"""
        for label in self:
            if not re.match(r'^L\d+$', label.name):
                raise ValidationError(_("Label number must be in format L000001!"))

    def _generate_pdf_label(self):
        """Generate PDF content for shipping label"""
        try:
            # Создаем PDF в памяти
            buffer = BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            
            # Добавляем содержимое этикетки
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(100, 750, "TRANSPORT LABEL")
            pdf.line(100, 745, 500, 745)
            
            pdf.setFont("Helvetica", 12)
            pdf.drawString(100, 700, f"Order Number: {self.order_id.name}")
            pdf.drawString(100, 675, f"Label Number: {self.name}")
            pdf.drawString(100, 650, f"Created: {self.create_date}")
            
            # Информация о товарах
            pdf.drawString(100, 600, "Items in order:")
            y_position = 575
            for item in self.order_id.item_ids:
                if y_position < 100:  # Новая страница если не хватает места
                    pdf.showPage()
                    y_position = 750
                pdf.drawString(120, y_position, f"• {item.item_code} - {item.product_name}")
                y_position -= 20
            
            # Штрих-код или QR-код (заглушка)
            pdf.drawString(100, 200, "📦 [BARCODE PLACEHOLDER]")
            
            pdf.save()
            
            # Сохраняем PDF в binary поле
            pdf_content = buffer.getvalue()
            buffer.close()
            
            self.write({
                'label_data': base64.b64encode(pdf_content),
                'label_filename': f'shipping_label_{self.name}.pdf'
            })
            
        except Exception as e:
            _logger.error("Error generating PDF label: %s", str(e))
            raise UserError(f"Error generating PDF: {str(e)}")

    def action_print_label(self):
        """Print the label and mark as printed"""
        self.ensure_one()
        if not self.printed:
            self.write({'printed': True})
        
        # Возвращаем действие для скачивания PDF
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/packaging.label/{self.id}/label_data/{self.label_filename}?download=true',
            'target': 'new',
        }

    def action_download_label(self):
        """Download the label PDF"""
        self.ensure_one()
        if not self.label_data:
            raise UserError("PDF label not generated yet!")
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/packaging.label/{self.id}/label_data/{self.label_filename}?download=true',
            'target': 'self',
        }

    def action_view_label(self):
        """View the label in browser"""
        self.ensure_one()
        if not self.label_data:
            raise UserError("PDF label not generated yet!")
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/packaging.label/{self.id}/label_data/{self.label_filename}',
            'target': 'new',
        }
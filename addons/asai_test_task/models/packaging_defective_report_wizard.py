from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import ast

class PackagingDefectiveReportWizard(models.TransientModel):
    _name = 'packaging.defective.report.wizard'
    _description = 'Defective Orders Report Wizard'

    report_data = fields.Text(string='Report Data')
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    responsible_id = fields.Many2one('res.users', string='Responsible')
    show_details = fields.Boolean(string='Show Details')
    pdf_report = fields.Binary(string='PDF Report')
    pdf_filename = fields.Char(string='PDF Filename')

    def get_report_data(self):
        """Parse and return report data"""
        self.ensure_one()
        if self.report_data:
            try:
                return ast.literal_eval(self.report_data)
            except (ValueError, SyntaxError):
                return []
        return []

    def action_print_report(self):
        """Generate and print PDF report"""
        self.ensure_one()
        
        report_data = self.get_report_data()
        if not report_data:
            raise UserError(_("No report data available"))
        
        # Generate PDF
        pdf_content = self._generate_pdf_report(report_data)
        
        # Save PDF to field
        self.write({
            'pdf_report': base64.b64encode(pdf_content),
            'pdf_filename': f'defective_orders_report_{fields.Date.today()}.pdf'
        })
        
        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/packaging.defective.report.wizard/{self.id}/pdf_report/{self.pdf_filename}?download=true',
            'target': 'self',
        }

    def _generate_pdf_report(self, report_data):
        """Generate PDF content for the report"""
        try:
            buffer = BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            
            # Header
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(100, 750, "DEFECTIVE ORDERS REPORT")
            pdf.line(100, 745, 500, 745)
            
            # Period
            pdf.setFont("Helvetica", 12)
            pdf.drawString(100, 720, f"Period: From {self.date_from} to {self.date_from}")
            
            # Responsible
            pdf.drawString(100, 700, f"Responsible: {self.responsible_id.name or 'All'}")
            
            # Orders data
            y_position = 650
            for order in report_data:
                if y_position < 100:
                    pdf.showPage()
                    y_position = 750
                    pdf.setFont("Helvetica", 12)
                
                pdf.setFont("Helvetica-Bold", 14)
                pdf.drawString(100, y_position, f"Order {order.get('order_number', '')} - {order.get('responsible', '')}")
                y_position -= 20
                
                pdf.setFont("Helvetica", 12)
                pdf.drawString(120, y_position, f"Defective Date: {order.get('defective_date', '')}")
                y_position -= 20
                
                pdf.drawString(120, y_position, f"Defective Items: {order.get('defective_items_count', 0)}/{order.get('total_items', 0)}")
                y_position -= 20
                
                pdf.drawString(120, y_position, f"Reason: {order.get('defective_reason', '')}")
                y_position -= 30
                
                # Item details
                if self.show_details and order.get('defective_items'):
                    pdf.drawString(120, y_position, "Defective Items Details:")
                    y_position -= 20
                    
                    for item in order.get('defective_items', []):
                        if y_position < 100:
                            pdf.showPage()
                            y_position = 750
                            pdf.setFont("Helvetica", 12)
                        
                        pdf.drawString(140, y_position, f"• {item.get('item_code', '')} - {item.get('product_name', '')}")
                        y_position -= 15
                        
                        pdf.drawString(160, y_position, f"Reason: {item.get('defective_reason', '')}")
                        y_position -= 15
                        
                        pdf.drawString(160, y_position, f"Reported by: {item.get('reported_by', '')} at {item.get('defective_date', '')}")
                        y_position -= 25
            
            pdf.save()
            pdf_content = buffer.getvalue()
            buffer.close()
            
            return pdf_content
            
        except Exception as e:
            raise UserError(_("Error generating PDF report: %s") % str(e))

    def action_export_excel(self):
        """Export report to Excel"""
        self.ensure_one()
        # Здесь можно добавить экспорт в Excel
        raise UserError(_("Excel export functionality not implemented yet"))
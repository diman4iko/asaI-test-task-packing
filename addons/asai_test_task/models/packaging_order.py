from odoo import models, fields, api, _
import base64
import csv
import io
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class PackagingOrder(models.Model):
    _name = 'packaging.order'
    _description = 'Packaging Order'
    _order = 'create_date desc'

    # ========== FIELDS ==========
    name = fields.Char(
        string='Order Number', 
        required=True, 
        default='New',
        tracking=True
    )
    responsible_id = fields.Many2one(
        'res.users', 
        string='Responsible Employee', 
        required=True,
        default=lambda self: self.env.user,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
        ('defective', 'Defective'),
    ], string='Status', default='draft', tracking=True)


    defective_reason = fields.Text(string='Defective Reason', help='Reason why the order cannot be completed')
    defective_date = fields.Datetime(string='Defective Date')
    defective_operator_id = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user)


    # Button visibility fields
    show_mark_completed = fields.Boolean(
        compute='_compute_button_visibility',
        string='Show Mark Completed'
    )
    show_reset_draft = fields.Boolean(
        compute='_compute_button_visibility',
        string='Show Reset Draft'
    )
    show_cancel_order = fields.Boolean(
        compute='_compute_button_visibility',
        string='Show Cancel Order'
    )

    # Relations
    item_ids = fields.One2many(
        'packaging.item', 
        'order_id', 
        string='Items in Order'
    )
    label_ids = fields.One2many(
        'packaging.label', 
        'order_id', 
        string='Shipping Labels'
    )

    # Progress tracking
    total_items = fields.Integer(
        string='Total Items', 
        compute='_compute_total_items',
        store=True
    )
    packed_items = fields.Integer(
        string='Packed Items', 
        compute='_compute_packed_items',
        store=True
    )
    progress = fields.Float(
        string='Progress (%)', 
        compute='_compute_progress'
    )


    defective_items = fields.Integer(
    string='Defective Items',
    compute='_compute_packed_items', 
    store=True
    )

    # Labels configuration
    last_label_id = fields.Many2one(
        'packaging.label', 
        string='Last Printed Label'
    )
    auto_print_labels = fields.Boolean(
        string='Auto-print Labels', 
        default=True
    )

    show_mark_defective = fields.Boolean(  
    compute='_compute_button_visibility',
    string='Show Mark Defective'
    )

    # Import/Export fields
    import_file = fields.Binary(string='Import CSV File')
    import_filename = fields.Char(string='Filename')

    # Quick actions fields
    quick_pack_item_code = fields.Char(string='Quick Pack by Item Code')
    quick_jump_order_number = fields.Integer(string='Quick Jump Order Number')

    # ========== COMPUTE METHODS ==========
    @api.depends('item_ids')
    def _compute_total_items(self):
        for order in self:
            order.total_items = len(order.item_ids)

    @api.depends('item_ids.is_packed')
    def _compute_packed_items(self):
        for order in self:
            packed_count = len(order.item_ids.filtered(lambda x: x.is_packed))
            order.packed_items = packed_count
            
            # Автоматическое обновление состояния только для сохраненных записей
            if order.id and order.state not in ['canceled', 'defective']:  # Исключаем defective
                if packed_count == order.total_items and order.total_items > 0:
                    if order.state != 'completed':
                        order.state = 'completed'
                        order._handle_completed_order()
                elif packed_count > 0:
                    if order.state != 'in_progress':
                        order.state = 'in_progress'
                else:
                    if order.state != 'draft':
                        order.state = 'draft'

    @api.depends('total_items', 'packed_items')
    def _compute_progress(self):
        for order in self:
            if order.total_items > 0:
                order.progress = (order.packed_items / order.total_items) * 100
            else:
                order.progress = 0

    @api.depends('state')
    def _compute_button_visibility(self):
        """Compute button visibility based on state"""
        for order in self:
            order.show_mark_completed = order.state in ['draft', 'in_progress']
            order.show_reset_draft = order.state in ['completed', 'canceled']
            order.show_cancel_order = order.state in ['draft', 'in_progress']
            order.show_mark_defective = order.state in ['draft', 'in_progress']


    @api.depends('item_ids.is_packed', 'item_ids.is_defective')  # Добавляем зависимость от is_defective
    def _compute_packed_items(self):
        for order in self:
            packed_count = len(order.item_ids.filtered(lambda x: x.is_packed))
            defective_count = len(order.item_ids.filtered(lambda x: x.is_defective))
            order.packed_items = packed_count
            
            # Автоматическое обновление состояния только для сохраненных записей
            if order.id and order.state not in ['canceled', 'defective']:
                if defective_count > 0:
                    if order.state != 'defective':
                        order.state = 'defective'
                        order.write({
                            'defective_reason': f'Automatic: {defective_count} defective item(s)',
                            'defective_date': fields.Datetime.now(),
                            'defective_operator_id': self.env.user.id
                        })
                # Старая логика для упаковки
                elif packed_count == order.total_items and order.total_items > 0:
                    if order.state != 'completed':
                        order.state = 'completed'
                        order._handle_completed_order()
                elif packed_count > 0:
                    if order.state != 'in_progress':
                        order.state = 'in_progress'
                else:
                    if order.state != 'draft':
                        order.state = 'draft'

    # ========== CRUD METHODS ==========
    @api.model
    def create(self, vals):
        """Override create to generate sequence number"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('packaging.order') or 'New'
        return super().create(vals)

    # ========== CONSTRAINT METHODS ==========
    @api.constrains('name')
    def _check_order_number(self):
        """Validate order number format"""
        for record in self:
            if record.name and not record.name.isdigit():
                raise ValidationError(_("Order number must contain only digits!"))

    # ========== BUSINESS LOGIC METHODS ==========
    def _handle_completed_order(self):
        """Handle actions when order is completed"""
        for order in self:
            if order.auto_print_labels and not order.label_ids:
                order._auto_print_shipping_label()

    def _auto_print_shipping_label(self):
        """Automatically generate shipping label for completed order"""
        try:
            # Убедимся что self.id существует
            if not self.id:
                _logger.error("Cannot create label - order not saved yet!")
                return
                
            label = self.env['packaging.label'].create({
                'order_id': self.id,  # Передаем корректный order_id
            })
            self.write({'last_label_id': label.id})  # Используем write вместо прямого присвоения
            _logger.info("Shipping label created for order %s", self.name)
        except Exception as e:
            _logger.error("Failed to create shipping label for order %s: %s", self.name, str(e))

    def action_manual_print_label(self):
        """Manually trigger label printing"""
        self.ensure_one()
        if self.state != 'completed':
            raise UserError(_("Cannot print label - order is not completed!"))
        return self._auto_print_shipping_label()

    def action_mark_completed(self):
        """Mark order as completed manually"""
        for order in self:
            if order.state not in ['draft', 'in_progress']:
                raise UserError(_("Cannot mark as completed from current state: %s") % order.state)
        self.write({'state': 'completed'})
        return self._show_notification(
            _("Order Completed"), 
            _("Order has been marked as completed"), 
            'success'
        )

    def action_reset_to_draft(self):
        """Reset order to draft state"""
        for order in self:
            if order.state not in ['completed', 'canceled']:
                raise UserError(_("Cannot reset to draft from current state: %s") % order.state)
        self.write({'state': 'draft'})
        return self._show_notification(
            _("Order Reset"), 
            _("Order has been reset to draft"), 
            'warning'
        )
    
    def action_mark_defective(self):
        """Mark order as defective with reason"""
        self.ensure_one()
        
        # Откроем wizard для указания причины брака
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mark as Defective',
            'res_model': 'packaging.order.defective.wizard',  # Изменяем на новую модель
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}  # Меняем контекст
        }
    
    def action_mark_defective_simple(self):
        """Simple method to mark order as defective without wizard"""
        self.ensure_one()
        
        # Просто помечаем заказ как бракованный
        self.write({
            'state': 'defective',
            'defective_reason': 'Marked as defective by operator',
            'defective_date': fields.Datetime.now(),
            'defective_operator_id': self.env.user.id
        })
        
        return self._show_notification(
            _("Order Marked as Defective"),
            _("Order has been marked as defective"),
            'warning'
        )

    def action_cancel_order(self):
        """Cancel the order"""
        for order in self:
            if order.state not in ['draft', 'in_progress']:
                raise UserError(_("Cannot cancel from current state: %s") % order.state)
        self.write({'state': 'canceled'})
        return self._show_notification(
            _("Order Canceled"), 
            _("Order has been canceled"), 
            'warning'
        )

    # ========== IMPORT/EXPORT METHODS ==========
    def action_import_csv(self):
        """Import items from CSV file"""
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Please select a CSV file to import"))
        
        try:
            items_created = self._process_csv_import()
            self._clear_import_fields()
            
            return self._show_notification(
                _("Import Successful"),
                _("Imported %d items") % items_created,
                'success'
            )
        except Exception as e:
            raise UserError(_("CSV Import Error: %s") % str(e))

    def _process_csv_import(self):
        """Process CSV file and create items"""
        file_content = base64.b64decode(self.import_file)
        file_stream = io.StringIO(file_content.decode('utf-8'))
        csv_reader = csv.DictReader(file_stream)
        
        items_created = 0
        for row in csv_reader:
            self._create_item_from_row(row)
            items_created += 1
            
        return items_created

    def _create_item_from_row(self, row):
        """Create packaging item from CSV row"""
        return self.env['packaging.item'].create({
            'order_id': self.id,
            'item_code': row.get('item_code', '').strip(),
            'product_name': row.get('product_name', '').strip(),
            'dimensions': row.get('dimensions', '').strip(),
        })

    def _clear_import_fields(self):
        """Clear import-related fields after processing"""
        self.write({'import_file': False, 'import_filename': False})

    # ========== QUICK ACTIONS METHODS ==========
    def action_quick_pack(self):
        """Quick pack item by code"""
        self.ensure_one()
        if not self.quick_pack_item_code:
            raise UserError(_("Please enter an item code"))
        
        item = self._find_item_by_code(self.quick_pack_item_code.strip())
        if not item:
            raise UserError(_("Item with code %s not found in this order") % self.quick_pack_item_code)
        if item.is_packed:
            raise UserError(_("Item %s is already packed") % self.quick_pack_item_code)
        
        item.action_mark_as_packed()
        self.write({'quick_pack_item_code': False})
        
        return self._show_notification(
            _("Item Packed"),
            _("Item %s marked as packed") % item.item_code,
            'success'
        )

    def _find_item_by_code(self, item_code):
        """Find item by code in current order"""
        return self.env['packaging.item'].search([
            ('order_id', '=', self.id),
            ('item_code', '=', item_code)
        ], limit=1)

    def action_quick_jump_to_order(self):
        """Quick jump to order by number"""
        if not self.quick_jump_order_number:
            raise UserError(_("Please enter an order number"))
        
        order = self.search([('name', '=', str(self.quick_jump_order_number))], limit=1)
        if not order:
            raise UserError(_("Order with number %s not found!") % self.quick_jump_order_number)
        
        return order.action_open_order()

    def action_open_order(self):
        """Open order in view mode"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('asai_test_task.view_packaging_order_form').id,
            'target': 'current',
        }

    # ========== UTILITY METHODS ==========
    def _show_notification(self, title, message, type='success'):
        """Show notification to user"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': type,
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    @api.model
    def get_formview_action(self, access_uid=None):
        """Override form view based on context"""
        result = super().get_formview_action(access_uid)
        if self.env.context.get('form_create_mode'):
            result['views'] = [
                (self.env.ref('asai_test_task.view_packaging_order_form_create').id, 'form')
            ]
        return result
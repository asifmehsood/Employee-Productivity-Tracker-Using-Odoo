from odoo import models, fields, api
from datetime import datetime


class ScreenshotLog(models.Model):
    _name = 'screenshot.log'
    _description = 'Screenshot Log'
    _order = 'create_date desc'

    task_id = fields.Many2one('productivity.task', string='Task', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', related='task_id.employee_id', store=True)
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id')
    
    screenshot_image = fields.Binary(string='Screenshot', attachment=True)
    image_filename = fields.Char(string='Filename')
    
    timestamp = fields.Datetime(string='Timestamp', default=lambda self: fields.Datetime.now(), readonly=True)
    
    # Activity tracking
    active_window = fields.Char(string='Active Window')
    active_application = fields.Char(string='Active Application')
    window_title = fields.Char(string='Window Title')
    
    # File info
    file_size = fields.Integer(string='File Size (bytes)')
    image_type = fields.Char(string='Image Type', default='image/png')
    
    # Optional metadata
    screen_width = fields.Integer(string='Screen Width')
    screen_height = fields.Integer(string='Screen Height')
    
    description = fields.Text(string='Description/Notes')
    
    # Productivity categorization
    is_productive = fields.Boolean(string='Is Productive', default=True, compute='_compute_productivity', store=True)
    
    create_date = fields.Datetime(string='Created', readonly=True)

    UNPRODUCTIVE_KEYWORDS = [
        'youtube', 'facebook', 'instagram', 'twitter', 'tiktok',
        'netflix', 'spotify', 'whatsapp', 'telegram', 'discord',
        'reddit', 'twitch', 'pinterest', 'snapchat', 'game'
    ]

    @api.depends('active_application', 'window_title')
    def _compute_productivity(self):
        """Determine if screenshot shows productive activity"""
        for record in self:
            is_productive = True
            if record.active_application or record.window_title:
                text = f"{record.active_application or ''} {record.window_title or ''}".lower()
                if any(keyword in text for keyword in self.UNPRODUCTIVE_KEYWORDS):
                    is_productive = False
            record.is_productive = is_productive

    @api.model
    def create(self, vals):
        """Create screenshot log entry"""
        if not vals.get('timestamp'):
            vals['timestamp'] = fields.Datetime.now()
        
        if vals.get('screenshot_image') and not vals.get('image_filename'):
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            vals['image_filename'] = f'screenshot_{timestamp}.png'
        
        return super().create(vals)

    def get_screenshot_base64(self):
        """Return screenshot as base64 for preview"""
        self.ensure_one()
        return self.screenshot_image

    def delete_screenshot(self):
        """Delete screenshot"""
        self.unlink()

    @api.model
    def cleanup_old_screenshots(self, days=30):
        """Delete screenshots older than specified days"""
        from datetime import datetime, timedelta
        cutoff_date = fields.Datetime.to_string(
            datetime.now() - timedelta(days=days)
        )
        old_screenshots = self.search([
            ('create_date', '<', cutoff_date)
        ])
        old_screenshots.unlink()
        return len(old_screenshots)

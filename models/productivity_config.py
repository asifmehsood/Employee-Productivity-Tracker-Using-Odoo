from odoo import models, fields, api


class ProductivityConfig(models.Model):
    _name = 'productivity.config'
    _description = 'Productivity Configuration'
    _singleton = True

    # Timer settings
    idle_timeout_minutes = fields.Integer(
        string='System Idle Timeout (minutes)',
        default=15,
        help='Automatically pause timer after X minutes of inactivity'
    )
    
    idle_detection_enabled = fields.Boolean(
        string='Enable Idle Detection',
        default=True
    )
    
    # Screenshot settings
    screenshot_interval_minutes = fields.Integer(
        string='Screenshot Interval (minutes)',
        default=10,
        help='Take screenshot every X minutes'
    )
    
    screenshot_enabled = fields.Boolean(
        string='Enable Automatic Screenshots',
        default=True
    )
    
    screenshot_retention_days = fields.Integer(
        string='Screenshot Retention (days)',
        default=30,
        help='Keep screenshots for X days, then delete automatically'
    )
    
    max_screenshot_size_kb = fields.Integer(
        string='Max Screenshot Size (KB)',
        default=500,
        help='Compress screenshots to max size'
    )
    
    # Restricted apps
    restricted_app_detection = fields.Boolean(
        string='Enable Restricted App Detection',
        default=True
    )
    
    restricted_apps = fields.Text(
        string='Restricted Applications',
        default='WhatsApp,YouTube,Spotify,Facebook,Instagram,TikTok,Twitter,Reddit,Netflix,Discord,Telegram,Steam,Twitch,Snapchat,Pinterest',
        help='Comma-separated list of apps to block. Pauses timer if detected.'
    )
    
    # Activity tracking
    track_keyboard_events = fields.Boolean(
        string='Track Keyboard Events',
        default=True
    )
    
    track_mouse_events = fields.Boolean(
        string='Track Mouse Events',
        default=True
    )
    
    # Manager notifications
    send_notifications = fields.Boolean(
        string='Send Manager Notifications',
        default=True
    )
    
    notify_on_restricted_app = fields.Boolean(
        string='Notify Manager on Restricted App Detection',
        default=True
    )
    
    notify_on_prolonged_idle = fields.Boolean(
        string='Notify Manager on Prolonged Idle',
        default=True
    )
    
    # Report settings
    auto_generate_reports = fields.Boolean(
        string='Auto-Generate Daily Reports',
        default=True
    )
    
    report_generation_time = fields.Char(
        string='Report Generation Time (HH:MM)',
        default='18:00',
        help='Time to automatically generate daily reports'
    )
    
    # Data retention
    delete_old_activity_logs = fields.Boolean(
        string='Auto-Delete Old Activity Logs',
        default=True
    )
    
    activity_log_retention_days = fields.Integer(
        string='Activity Log Retention (days)',
        default=90,
        help='Keep activity logs for X days, then delete'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.model
    def get_config(self):
        """Get or create configuration"""
        config = self.search([], limit=1)
        if not config:
            config = self.create({})
        return config

    def get_restricted_apps_list(self):
        """Get list of restricted apps"""
        if self.restricted_apps:
            return [app.strip() for app in self.restricted_apps.split(',')]
        return []

    @api.model
    def cleanup_old_data(self):
        """Clean up old screenshots and activity logs based on retention settings"""
        config = self.get_config()
        
        # Clean up old screenshots
        if config.screenshot_retention_days > 0:
            from datetime import datetime, timedelta
            from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
            
            cutoff_date = datetime.now() - timedelta(days=config.screenshot_retention_days)
            self.env['screenshot.log'].search([
                ('create_date', '<', cutoff_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            ]).unlink()
        
        # Clean up old activity logs
        if config.delete_old_activity_logs and config.activity_log_retention_days > 0:
            from datetime import datetime, timedelta
            from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
            
            cutoff_date = datetime.now() - timedelta(days=config.activity_log_retention_days)
            self.env['activity.log'].search([
                ('create_date', '<', cutoff_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            ]).unlink()

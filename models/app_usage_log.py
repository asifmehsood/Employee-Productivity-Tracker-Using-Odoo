from odoo import models, fields, api


class AppUsageLog(models.Model):
    _name = 'app.usage.log'
    _description = 'Application Usage Log'
    _order = 'start_time desc'

    task_id = fields.Many2one('productivity.task', string='Task', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id', store=True)
    
    app_name = fields.Char(string='Application Name', required=True)
    app_path = fields.Char(string='Application Path')
    
    start_time = fields.Datetime(string='Start Time', default=lambda self: fields.Datetime.now())
    end_time = fields.Datetime(string='End Time')
    
    duration = fields.Float(string='Duration (Minutes)', compute='_compute_duration', store=True)
    
    is_restricted = fields.Boolean(string='Is Restricted App', compute='_compute_restricted', store=True)
    
    app_category = fields.Selection([
        ('work', 'Work'),
        ('communication', 'Communication'),
        ('entertainment', 'Entertainment'),
        ('social_media', 'Social Media'),
        ('other', 'Other'),
    ], string='App Category', default='other')
    
    window_title = fields.Char(string='Window Title')
    
    create_date = fields.Datetime(string='Created', readonly=True)

    RESTRICTED_APPS = [
        'whatsapp', 'youtube', 'spotify', 'facebook',
        'instagram', 'tiktok', 'twitter', 'reddit',
        'netflix', 'discord', 'telegram', 'steam',
        'twitch', 'snapchat', 'pinterest', 'tinder',
        'bumble', 'hulu', 'amazon prime', 'disneyplus'
    ]

    WORK_APPS = [
        'outlook', 'excel', 'word', 'powerpoint',
        'slack', 'teams', 'zoom', 'chrome', 'firefox',
        'vscode', 'notepad', 'visual studio', 'datagrip',
        'jira', 'confluence', 'salesforce', 'sap'
    ]

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        """Compute duration in minutes"""
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration = delta.total_seconds() / 60
            else:
                record.duration = 0

    @api.depends('app_name')
    def _compute_restricted(self):
        """Check if app is in restricted list"""
        for record in self:
            app_lower = record.app_name.lower() if record.app_name else ''
            record.is_restricted = any(
                restricted in app_lower for restricted in self.RESTRICTED_APPS
            )

    @api.model
    def create(self, vals):
        """Create app usage log and categorize app"""
        if vals.get('app_name'):
            app_name = vals['app_name'].lower()
            
            # Categorize app
            if any(work in app_name for work in self.WORK_APPS):
                vals['app_category'] = 'work'
            elif any(comm in app_name for comm in ['slack', 'teams', 'outlook', 'telegram', 'whatsapp']):
                vals['app_category'] = 'communication'
            elif any(ent in app_name for ent in ['youtube', 'netflix', 'spotify', 'hulu', 'twitch']):
                vals['app_category'] = 'entertainment'
            elif any(social in app_name for social in ['facebook', 'instagram', 'twitter', 'tiktok', 'reddit']):
                vals['app_category'] = 'social_media'
        
        return super().create(vals)

    @api.model
    def get_app_usage_summary(self, task_id):
        """Get summary of app usage for a task"""
        apps = self.search([('task_id', '=', task_id)])
        
        summary = {}
        for app in apps:
            if app.app_name not in summary:
                summary[app.app_name] = {
                    'duration': 0,
                    'count': 0,
                    'category': app.app_category,
                    'is_restricted': app.is_restricted,
                }
            summary[app.app_name]['duration'] += app.duration or 0
            summary[app.app_name]['count'] += 1
        
        return summary

    @api.model
    def log_app_usage(self, task_id, employee_id, app_name, app_path=None, window_title=None):
        """Log app usage"""
        vals = {
            'task_id': task_id,
            'employee_id': employee_id,
            'app_name': app_name,
            'start_time': fields.Datetime.now(),
        }
        
        if app_path:
            vals['app_path'] = app_path
        if window_title:
            vals['window_title'] = window_title
        
        return self.create(vals)

    @api.model
    def get_employee_app_summary(self, employee_id, date_from, date_to):
        """Get app usage summary for an employee in a date range"""
        apps = self.search([
            ('employee_id', '=', employee_id),
            ('start_time', '>=', date_from),
            ('start_time', '<=', date_to),
        ])
        
        summary = {}
        for app in apps:
            if app.app_name not in summary:
                summary[app.app_name] = {
                    'duration': 0,
                    'count': 0,
                    'category': app.app_category,
                }
            summary[app.app_name]['duration'] += app.duration or 0
            summary[app.app_name]['count'] += 1
        
        return summary

    def end_app_usage(self):
        """End app usage session"""
        self.ensure_one()
        self.write({
            'end_time': fields.Datetime.now(),
        })

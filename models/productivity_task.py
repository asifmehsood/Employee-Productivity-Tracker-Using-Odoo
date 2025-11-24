from odoo import models, fields, api
from datetime import datetime, timedelta


class ProductivityTask(models.Model):
    _name = 'productivity.task'
    _description = 'Productivity Task'
    _order = 'create_date desc'

    name = fields.Char(string='Task Name', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id')
    
    # Timer fields
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    ], default='draft', string='State')
    
    start_time = fields.Datetime(string='Start Time')
    stop_time = fields.Datetime(string='Stop Time')
    timer_display = fields.Char(string='Real-Time Timer', compute='_compute_timer_display')
    total_working_time = fields.Float(string='Total Working Time (Hours)', compute='_compute_total_time', store=True)
    total_paused_time = fields.Float(string='Total Paused Time (Hours)', compute='_compute_paused_time', store=True)
    
    # Pause tracking
    pause_time = fields.Datetime(string='Last Pause Time')
    pause_count = fields.Integer(string='Pause Count', default=0)
    
    # Activity tracking
    is_idle = fields.Boolean(string='Is Idle', default=False)
    idle_start_time = fields.Datetime(string='Idle Start Time')
    
    # Relations
    # screenshot_ids = fields.One2many('screenshot.log', 'task_id', string='Screenshots')  # Screenshot functionality removed
    activity_log_ids = fields.One2many('activity.log', 'task_id', string='Activity Logs')
    app_usage_ids = fields.One2many('app.usage.log', 'task_id', string='App Usage')
    
    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes')
    
    create_date = fields.Datetime(string='Created', readonly=True)
    write_date = fields.Datetime(string='Modified', readonly=True)

    @api.depends('start_time', 'state')
    def _compute_timer_display(self):
        """Compute real-time timer display - updated by frontend"""
        for record in self:
            if record.state == 'running' and record.start_time:
                elapsed = (fields.Datetime.now() - record.start_time).total_seconds()
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                record.timer_display = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                record.timer_display = "00:00:00"

    @api.depends('start_time', 'stop_time', 'pause_time')
    def _compute_total_time(self):
        """Compute total working time in hours"""
        for record in self:
            if record.start_time:
                end_time = record.stop_time or fields.Datetime.now()
                total_seconds = (end_time - record.start_time).total_seconds()
                
                # Subtract paused time
                paused_records = self.env['activity.log'].search([
                    ('task_id', '=', record.id),
                    ('activity_type', '=', 'pause')
                ])
                
                paused_seconds = 0
                for pause in paused_records:
                    if pause.end_time:
                        paused_seconds += (pause.end_time - pause.start_time).total_seconds()
                
                total_working_seconds = max(0, total_seconds - paused_seconds)
                record.total_working_time = total_working_seconds / 3600  # Convert to hours
            else:
                record.total_working_time = 0

    @api.depends('total_working_time', 'start_time', 'stop_time')
    def _compute_paused_time(self):
        """Compute total paused time in hours"""
        for record in self:
            if record.start_time:
                paused_records = self.env['activity.log'].search([
                    ('task_id', '=', record.id),
                    ('activity_type', '=', 'pause')
                ])
                
                total_paused_seconds = 0
                for pause in paused_records:
                    if pause.end_time:
                        total_paused_seconds += (pause.end_time - pause.start_time).total_seconds()
                
                record.total_paused_time = total_paused_seconds / 3600  # Convert to hours
            else:
                record.total_paused_time = 0

    def action_start_timer(self):
        """Start the timer"""
        self.ensure_one()
        from datetime import timedelta
        import logging
        _logger = logging.getLogger(__name__)
        
        now = fields.Datetime.now()
        
        # If user set a stop_time, use it if it's in the future
        # Otherwise default to 8 hours from now
        if self.stop_time and self.stop_time > now:
            stop_time = self.stop_time
            _logger.info(f'Using user-defined stop_time: {stop_time} (in {(stop_time - now).total_seconds()} seconds)')
        else:
            # Default to 8 hours from now
            stop_time = now + timedelta(hours=8)
            _logger.info(f'Using default stop_time: {stop_time} (8 hours from now)')
        
        _logger.info(f'Timer starting - Now: {now}, Stop: {stop_time}')
        
        self.write({
            'state': 'running',
            'start_time': now,
            'stop_time': stop_time,
        })
        self.env['activity.log'].create({
            'task_id': self.id,
            'employee_id': self.employee_id.id,
            'activity_type': 'timer_start',
            'start_time': now,
            'description': 'Timer started for task: ' + self.name,
        })
        # Don't reload to prevent interrupting the timer widget
        return True

    def action_stop_timer(self):
        """Stop the timer"""
        self.ensure_one()
        self.write({
            'state': 'completed',
            'stop_time': fields.Datetime.now(),
        })
        self.env['activity.log'].create({
            'task_id': self.id,
            'employee_id': self.employee_id.id,
            'activity_type': 'timer_stop',
            'start_time': fields.Datetime.now(),
            'description': 'Timer stopped for task: ' + self.name,
        })
        return True

    def action_pause_timer(self):
        """Pause the timer"""
        self.ensure_one()
        self.write({
            'state': 'paused',
            'pause_time': fields.Datetime.now(),
            'pause_count': self.pause_count + 1,
        })
        self.env['activity.log'].create({
            'task_id': self.id,
            'employee_id': self.employee_id.id,
            'activity_type': 'pause',
            'start_time': fields.Datetime.now(),
            'description': 'Timer paused for task: ' + self.name,
        })
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_resume_timer(self):
        """Resume the timer"""
        self.ensure_one()
        self.write({
            'state': 'running',
            'pause_time': False,
        })
        last_pause = self.env['activity.log'].search([
            ('task_id', '=', self.id),
            ('activity_type', '=', 'pause')
        ], order='start_time desc', limit=1)
        
        if last_pause:
            last_pause.write({
                'end_time': fields.Datetime.now(),
            })
        
        self.env['activity.log'].create({
            'task_id': self.id,
            'employee_id': self.employee_id.id,
            'activity_type': 'resume',
            'start_time': fields.Datetime.now(),
            'description': 'Timer resumed for task: ' + self.name,
        })
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def detect_idle(self, idle_timeout_minutes=15):
        """Check if system is idle and pause timer if needed"""
        for record in self:
            if record.state == 'running' and record.start_time:
                # This would be called from the agent/cron job
                # For now, marking as idle if needed
                now = fields.Datetime.now()
                # Idle detection logic would go here
                pass

    def detect_restricted_apps(self, detected_apps):
        """Check if restricted apps are running and pause if needed"""
        restricted_apps = [
            'whatsapp', 'youtube', 'spotify', 'facebook',
            'instagram', 'tiktok', 'twitter', 'reddit',
            'netflix', 'discord', 'telegram', 'steam'
        ]
        
        for app in detected_apps:
            if any(restricted in app.lower() for restricted in restricted_apps):
                for record in self:
                    if record.state == 'running':
                        self.action_pause_timer()
                        self.env['activity.log'].create({
                            'task_id': record.id,
                            'employee_id': record.employee_id.id,
                            'activity_type': 'restricted_app_detected',
                            'start_time': fields.Datetime.now(),
                            'description': f'Restricted app detected: {app}. Timer paused.',
                        })
                        return

    @api.model
    def create(self, vals):
        """Override create to set employee from current user if not provided"""
        if not vals.get('employee_id'):
            employee = self.env['hr.employee'].search([
                ('user_id', '=', self.env.user.id)
            ], limit=1)
            if employee:
                vals['employee_id'] = employee.id
        return super().create(vals)

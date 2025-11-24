from odoo import models, fields, api


class ActivityLog(models.Model):
    _name = 'activity.log'
    _description = 'Activity Log'
    _order = 'start_time desc'

    task_id = fields.Many2one('productivity.task', string='Task', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id', store=True)
    
    activity_type = fields.Selection([
        ('timer_start', 'Timer Started'),
        ('timer_stop', 'Timer Stopped'),
        ('pause', 'Paused'),
        ('resume', 'Resumed'),
        ('idle_detected', 'Idle Detected'),
        ('idle_cleared', 'Idle Cleared'),
        ('restricted_app_detected', 'Restricted App Detected'),
        ('system_activity', 'System Activity'),
        ('user_activity', 'User Activity'),
        ('screenshot_captured', 'Screenshot Captured'),
    ], string='Activity Type', required=True)
    
    start_time = fields.Datetime(string='Start Time', required=True, default=lambda self: fields.Datetime.now())
    end_time = fields.Datetime(string='End Time')
    
    duration = fields.Float(string='Duration (Minutes)', compute='_compute_duration', store=True)
    
    description = fields.Text(string='Description')
    app_name = fields.Char(string='Application Name')
    
    keyboard_events = fields.Integer(string='Keyboard Events', default=0)
    mouse_events = fields.Integer(string='Mouse Events', default=0)
    
    create_date = fields.Datetime(string='Created', readonly=True)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        """Compute duration in minutes"""
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration = delta.total_seconds() / 60
            else:
                record.duration = 0

    @api.model
    def log_activity(self, task_id, employee_id, activity_type, description='', app_name=None, **kwargs):
        """Log an activity"""
        vals = {
            'task_id': task_id,
            'employee_id': employee_id,
            'activity_type': activity_type,
            'description': description,
            'start_time': fields.Datetime.now(),
        }
        
        if app_name:
            vals['app_name'] = app_name
        
        vals.update(kwargs)
        return self.create(vals)

    @api.model
    def get_activity_summary(self, task_id):
        """Get summary of activities for a task"""
        activities = self.search([('task_id', '=', task_id)])
        
        summary = {
            'total_activities': len(activities),
            'timer_starts': len(activities.filtered(lambda a: a.activity_type == 'timer_start')),
            'pauses': len(activities.filtered(lambda a: a.activity_type == 'pause')),
            'resumptions': len(activities.filtered(lambda a: a.activity_type == 'resume')),
            'idle_detections': len(activities.filtered(lambda a: a.activity_type == 'idle_detected')),
            'restricted_apps_detected': len(activities.filtered(lambda a: a.activity_type == 'restricted_app_detected')),
        }
        
        return summary

    @api.model
    def get_employee_daily_summary(self, employee_id, date):
        """Get daily summary for an employee"""
        from datetime import datetime, timedelta
        
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())
        
        activities = self.search([
            ('employee_id', '=', employee_id),
            ('start_time', '>=', start_of_day),
            ('start_time', '<=', end_of_day),
        ])
        
        return activities

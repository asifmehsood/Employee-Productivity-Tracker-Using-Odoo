from odoo import models, fields, api
from datetime import datetime, timedelta


class ProductivityDashboard(models.Model):
    _name = 'productivity.dashboard'
    _description = 'Productivity Dashboard Statistics'
    _auto = False  # This is a SQL view model

    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    
    # Current status
    is_currently_active = fields.Boolean(string='Currently Active', readonly=True)
    current_task_id = fields.Many2one('productivity.task', string='Current Task', readonly=True)
    
    # Statistics (today)
    total_tasks_today = fields.Integer(string='Tasks Today', readonly=True)
    total_working_hours_today = fields.Float(string='Working Hours Today', readonly=True)
    total_paused_hours_today = fields.Float(string='Paused Hours Today', readonly=True)
    productive_time_today = fields.Float(string='Productive Time Today', readonly=True)
    
    # Screenshots
    total_screenshots_today = fields.Integer(string='Screenshots Today', readonly=True)
    productive_screenshots = fields.Integer(string='Productive Screenshots', readonly=True)
    unproductive_screenshots = fields.Integer(string='Unproductive Screenshots', readonly=True)
    
    # App usage
    most_used_app_today = fields.Char(string='Most Used App', readonly=True)
    
    # Weekly stats
    total_working_hours_week = fields.Float(string='Working Hours This Week', readonly=True)
    total_tasks_week = fields.Integer(string='Tasks This Week', readonly=True)
    
    def init(self):
        """Create SQL view for dashboard statistics"""
        self._cr.execute("""
            CREATE OR REPLACE VIEW productivity_dashboard AS (
                SELECT 
                    row_number() OVER () as id,
                    e.id as employee_id,
                    e.user_id as user_id,
                    
                    EXISTS(
                        SELECT 1 FROM productivity_task pt 
                        WHERE pt.employee_id = e.id 
                        AND pt.state = 'running'
                        LIMIT 1
                    ) as is_currently_active,
                    
                    (
                        SELECT id FROM productivity_task pt 
                        WHERE pt.employee_id = e.id 
                        AND pt.state = 'running'
                        ORDER BY start_time DESC
                        LIMIT 1
                    ) as current_task_id,
                    
                    (
                        SELECT COUNT(*) FROM productivity_task pt
                        WHERE pt.employee_id = e.id
                        AND DATE(pt.start_time AT TIME ZONE 'UTC') = CURRENT_DATE
                    ) as total_tasks_today,
                    
                    (
                        SELECT COALESCE(SUM(pt.total_working_time), 0) FROM productivity_task pt
                        WHERE pt.employee_id = e.id
                        AND DATE(pt.start_time AT TIME ZONE 'UTC') = CURRENT_DATE
                    ) as total_working_hours_today,
                    
                    (
                        SELECT COALESCE(SUM(pt.total_paused_time), 0) FROM productivity_task pt
                        WHERE pt.employee_id = e.id
                        AND DATE(pt.start_time AT TIME ZONE 'UTC') = CURRENT_DATE
                    ) as total_paused_hours_today,
                    
                    (
                        SELECT COALESCE(SUM(pt.total_working_time), 0) FROM productivity_task pt
                        WHERE pt.employee_id = e.id
                        AND DATE(pt.start_time AT TIME ZONE 'UTC') = CURRENT_DATE
                    ) as productive_time_today,
                    
                    (
                        SELECT COUNT(*) FROM screenshot_log sl
                        INNER JOIN productivity_task pt ON sl.task_id = pt.id
                        WHERE pt.employee_id = e.id
                        AND DATE(sl.timestamp AT TIME ZONE 'UTC') = CURRENT_DATE
                    ) as total_screenshots_today,
                    
                    (
                        SELECT COUNT(*) FROM screenshot_log sl
                        INNER JOIN productivity_task pt ON sl.task_id = pt.id
                        WHERE pt.employee_id = e.id
                        AND sl.is_productive = true
                        AND DATE(sl.timestamp AT TIME ZONE 'UTC') = CURRENT_DATE
                    ) as productive_screenshots,
                    
                    (
                        SELECT COUNT(*) FROM screenshot_log sl
                        INNER JOIN productivity_task pt ON sl.task_id = pt.id
                        WHERE pt.employee_id = e.id
                        AND sl.is_productive = false
                        AND DATE(sl.timestamp AT TIME ZONE 'UTC') = CURRENT_DATE
                    ) as unproductive_screenshots,
                    
                    (
                        SELECT aul.app_name FROM app_usage_log aul
                        INNER JOIN productivity_task pt ON aul.task_id = pt.id
                        WHERE pt.employee_id = e.id
                        AND DATE(aul.start_time AT TIME ZONE 'UTC') = CURRENT_DATE
                        GROUP BY aul.app_name
                        ORDER BY SUM(aul.duration) DESC
                        LIMIT 1
                    ) as most_used_app_today,
                    
                    (
                        SELECT COALESCE(SUM(pt.total_working_time), 0) FROM productivity_task pt
                        WHERE pt.employee_id = e.id
                        AND pt.start_time >= (CURRENT_DATE - INTERVAL '7 days')
                    ) as total_working_hours_week,
                    
                    (
                        SELECT COUNT(*) FROM productivity_task pt
                        WHERE pt.employee_id = e.id
                        AND pt.start_time >= (CURRENT_DATE - INTERVAL '7 days')
                    ) as total_tasks_week
                    
                FROM hr_employee e
                WHERE e.active = true
            )
        """)


class ProductivitySummaryReport(models.TransientModel):
    _name = 'productivity.summary.report'
    _description = 'Productivity Summary Report Generator'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date_from = fields.Date(string='From Date', required=True, default=lambda self: fields.Date.today())
    date_to = fields.Date(string='To Date', required=True, default=lambda self: fields.Date.today())
    
    # Summary fields
    total_tasks = fields.Integer(string='Total Tasks', compute='_compute_summary')
    total_working_hours = fields.Float(string='Total Working Hours', compute='_compute_summary')
    total_paused_hours = fields.Float(string='Total Paused Hours', compute='_compute_summary')
    total_screenshots = fields.Integer(string='Total Screenshots', compute='_compute_summary')
    productive_screenshots = fields.Integer(string='Productive Screenshots', compute='_compute_summary')
    unproductive_screenshots = fields.Integer(string='Unproductive Screenshots', compute='_compute_summary')
    productivity_score = fields.Float(string='Productivity Score %', compute='_compute_summary')
    
    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_summary(self):
        for record in self:
            tasks = self.env['productivity.task'].search([
                ('employee_id', '=', record.employee_id.id),
                ('start_time', '>=', fields.Datetime.to_string(datetime.combine(record.date_from, datetime.min.time()))),
                ('start_time', '<=', fields.Datetime.to_string(datetime.combine(record.date_to, datetime.max.time()))),
            ])
            
            record.total_tasks = len(tasks)
            record.total_working_hours = sum(tasks.mapped('total_working_time'))
            record.total_paused_hours = sum(tasks.mapped('total_paused_time'))
            
            screenshots = self.env['screenshot.log'].search([
                ('task_id', 'in', tasks.ids),
            ])
            
            record.total_screenshots = len(screenshots)
            record.productive_screenshots = len(screenshots.filtered(lambda s: s.is_productive))
            record.unproductive_screenshots = len(screenshots.filtered(lambda s: not s.is_productive))
            
            if record.total_screenshots > 0:
                record.productivity_score = (record.productive_screenshots / record.total_screenshots) * 100
            else:
                record.productivity_score = 0
    
    def action_view_tasks(self):
        """View tasks in the date range"""
        self.ensure_one()
        return {
            'name': f'Tasks for {self.employee_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'productivity.task',
            'view_mode': 'list,form',
            'domain': [
                ('employee_id', '=', self.employee_id.id),
                ('start_time', '>=', fields.Datetime.to_string(datetime.combine(self.date_from, datetime.min.time()))),
                ('start_time', '<=', fields.Datetime.to_string(datetime.combine(self.date_to, datetime.max.time()))),
            ],
        }
    
    def action_view_screenshots(self):
        """View screenshot gallery"""
        self.ensure_one()
        task_ids = self.env['productivity.task'].search([
            ('employee_id', '=', self.employee_id.id),
            ('start_time', '>=', fields.Datetime.to_string(datetime.combine(self.date_from, datetime.min.time()))),
            ('start_time', '<=', fields.Datetime.to_string(datetime.combine(self.date_to, datetime.max.time()))),
        ]).ids
        
        return {
            'name': f'Screenshots for {self.employee_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'screenshot.log',
            'view_mode': 'kanban,list,form',
            'domain': [('task_id', 'in', task_ids)],
        }
    
    def action_export_report(self):
        """Export report to Excel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/productivity/export_report?employee_id={self.employee_id.id}&date_from={self.date_from}&date_to={self.date_to}',
            'target': 'new',
        }

from odoo import models, fields, api
from datetime import datetime, timedelta


class ProductivityReport(models.Model):
    _name = 'productivity.report'
    _description = 'Productivity Report'
    _order = 'period_end desc'

    name = fields.Char(string='Report Name', required=True, compute='_compute_name', store=True)
    
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id', store=True)
    
    # Period
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    
    report_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], string='Report Type', default='daily')
    
    # Summary metrics
    total_working_hours = fields.Float(string='Total Working Hours', compute='_compute_metrics', store=True)
    total_paused_hours = fields.Float(string='Total Paused Hours', compute='_compute_metrics', store=True)
    total_idle_hours = fields.Float(string='Total Idle Hours', compute='_compute_metrics', store=True)
    productivity_percentage = fields.Float(string='Productivity %', compute='_compute_metrics', store=True)
    
    tasks_completed = fields.Integer(string='Tasks Completed', compute='_compute_metrics', store=True)
    # screenshots_captured = fields.Integer(string='Screenshots Captured', compute='_compute_metrics', store=True)  # Screenshot functionality removed
    
    # App usage
    most_used_app = fields.Char(string='Most Used App')
    restricted_app_time = fields.Float(string='Restricted App Time (Hours)')
    
    # Details
    task_ids = fields.Many2many('productivity.task', string='Tasks Included')
    # screenshot_ids = fields.Many2many('screenshot.log', string='Screenshots')  # Screenshot functionality removed
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('reviewed', 'Reviewed'),
    ], string='State', default='draft')
    
    notes = fields.Text(string='Manager Notes')
    
    # Export
    pdf_report = fields.Binary(string='PDF Report', attachment=True)
    excel_report = fields.Binary(string='Excel Report', attachment=True)
    
    create_date = fields.Datetime(string='Created', readonly=True)

    @api.depends('employee_id', 'period_start', 'period_end', 'report_type')
    def _compute_name(self):
        """Compute report name"""
        for record in self:
            if record.employee_id and record.period_start and record.period_end:
                emp_name = record.employee_id.name
                period = f"{record.period_start} to {record.period_end}"
                record.name = f"Productivity Report - {emp_name} ({period})"
            else:
                record.name = "Productivity Report"

    @api.depends('period_start', 'period_end', 'employee_id')
    def _compute_metrics(self):
        """Compute productivity metrics"""
        for record in self:
            if record.employee_id and record.period_start and record.period_end:
                # Get all tasks for this employee in the period
                tasks = self.env['productivity.task'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('create_date', '>=', f"{record.period_start} 00:00:00"),
                    ('create_date', '<=', f"{record.period_end} 23:59:59"),
                ])
                
                total_work = sum(task.total_working_time for task in tasks)
                total_paused = sum(task.total_paused_time for task in tasks)
                
                # Calculate metrics
                record.total_working_hours = total_work
                record.total_paused_hours = total_paused
                record.tasks_completed = len(tasks.filtered(lambda t: t.state == 'completed'))
                
                # Screenshots - functionality removed
                # screenshots = self.env['screenshot.log'].search([
                #     ('employee_id', '=', record.employee_id.id),
                #     ('create_date', '>=', f"{record.period_start} 00:00:00"),
                #     ('create_date', '<=', f"{record.period_end} 23:59:59"),
                # ])
                # record.screenshot_ids = screenshots
                # record.screenshots_captured = len(screenshots)
                
                # Calculate productivity percentage
                total_time = total_work + total_paused
                if total_time > 0:
                    record.productivity_percentage = (total_work / total_time) * 100
                else:
                    record.productivity_percentage = 0
                
                # Get app usage summary
                app_usage = self.env['app.usage.log'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('start_time', '>=', f"{record.period_start} 00:00:00"),
                    ('start_time', '<=', f"{record.period_end} 23:59:59"),
                ])
                
                if app_usage:
                    # Find most used app
                    app_durations = {}
                    for usage in app_usage:
                        if usage.app_name not in app_durations:
                            app_durations[usage.app_name] = 0
                        app_durations[usage.app_name] += usage.duration or 0
                    
                    if app_durations:
                        most_used = max(app_durations, key=app_durations.get)
                        record.most_used_app = most_used
                    
                    # Calculate restricted app time
                    restricted_time = sum(
                        usage.duration or 0 for usage in app_usage
                        if usage.is_restricted
                    )
                    record.restricted_app_time = restricted_time / 60  # Convert to hours
                
                record.task_ids = tasks
            else:
                record.total_working_hours = 0
                record.total_paused_hours = 0
                record.total_idle_hours = 0
                record.productivity_percentage = 0
                record.tasks_completed = 0
                # record.screenshots_captured = 0  # Screenshot functionality removed

    @api.model
    def generate_report(self, employee_id, period_start, period_end, report_type='daily'):
        """Generate a productivity report"""
        existing = self.search([
            ('employee_id', '=', employee_id),
            ('period_start', '=', period_start),
            ('period_end', '=', period_end),
            ('report_type', '=', report_type),
        ])
        
        if existing:
            return existing[0]
        
        report = self.create({
            'employee_id': employee_id,
            'period_start': period_start,
            'period_end': period_end,
            'report_type': report_type,
            'state': 'generated',
        })
        
        return report

    @api.model
    def generate_daily_reports(self):
        """Generate daily reports for all employees"""
        yesterday = datetime.now().date() - timedelta(days=1)
        
        employees = self.env['hr.employee'].search([])
        
        for employee in employees:
            self.generate_report(
                employee.id,
                yesterday,
                yesterday,
                'daily'
            )

    def export_to_pdf(self):
        """Export report to PDF"""
        # This would typically use report generation library
        # For now, we'll just mark it as exported
        self.ensure_one()
        self.write({
            'state': 'reviewed',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/productivity_report/' + str(self.id),
        }

    def export_to_excel(self):
        """Export report to Excel"""
        # This would use a library like openpyxl
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/export/excel/productivity_report/' + str(self.id),
        }

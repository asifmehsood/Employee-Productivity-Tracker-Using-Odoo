from odoo import http, fields
from odoo.http import request
import base64
import json


class ProductivityTrackerController(http.Controller):
    """Main controller for productivity tracking API endpoints"""

    @http.route('/api/productivity/start_task', type='json', auth='user', methods=['POST'])
    def start_task(self, **kwargs):
        """Start a new productivity task"""
        try:
            task_name = kwargs.get('task_name', 'Unnamed Task')
            description = kwargs.get('description', '')
            
            employee = request.env['hr.employee'].search([
                ('user_id', '=', request.env.user.id)
            ], limit=1)
            
            if not employee:
                return {'status': 'error', 'message': 'Employee not found'}
            
            task = request.env['productivity.task'].create({
                'name': task_name,
                'description': description,
                'employee_id': employee.id,
                'state': 'running',
                'start_time': fields.Datetime.now(),
            })
            
            return {
                'status': 'success',
                'task_id': task.id,
                'message': f'Task {task_name} started'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/productivity/stop_task/<int:task_id>', type='json', auth='user', methods=['POST'])
    def stop_task(self, task_id, **kwargs):
        """Stop a productivity task"""
        try:
            task = request.env['productivity.task'].browse(task_id)
            
            if not task:
                return {'status': 'error', 'message': 'Task not found'}
            
            task.action_stop_timer()
            
            return {
                'status': 'success',
                'task_id': task.id,
                'total_time': task.total_working_time,
                'message': f'Task {task.name} stopped'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/productivity/pause_task/<int:task_id>', type='json', auth='user', methods=['POST'])
    def pause_task(self, task_id, **kwargs):
        """Pause a productivity task"""
        try:
            task = request.env['productivity.task'].browse(task_id)
            task.action_pause_timer()
            
            return {'status': 'success', 'message': f'Task {task.name} paused'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/productivity/resume_task/<int:task_id>', type='json', auth='user', methods=['POST'])
    def resume_task(self, task_id, **kwargs):
        """Resume a productivity task"""
        try:
            task = request.env['productivity.task'].browse(task_id)
            task.action_resume_timer()
            
            return {'status': 'success', 'message': f'Task {task.name} resumed'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    # Screenshot functionality removed
    # @http.route('/api/productivity/upload_screenshot', type='json', auth='user', methods=['POST'])
    # def upload_screenshot(self, **kwargs):
    #     """Upload a screenshot with activity context"""
    #     pass

    @http.route('/api/productivity/log_activity', type='json', auth='user', methods=['POST'])
    def log_activity(self, **kwargs):
        """Log an activity"""
        try:
            task_id = kwargs.get('task_id')
            activity_type = kwargs.get('activity_type')
            description = kwargs.get('description', '')
            app_name = kwargs.get('app_name')
            
            task = request.env['productivity.task'].browse(task_id)
            
            activity_log = request.env['activity.log'].log_activity(
                task_id=task.id,
                employee_id=task.employee_id.id,
                activity_type=activity_type,
                description=description,
                app_name=app_name,
            )
            
            return {
                'status': 'success',
                'activity_id': activity_log.id,
                'message': 'Activity logged'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/productivity/log_app_usage', type='json', auth='user', methods=['POST'])
    def log_app_usage(self, **kwargs):
        """Log application usage"""
        try:
            task_id = kwargs.get('task_id')
            app_name = kwargs.get('app_name')
            app_path = kwargs.get('app_path')
            window_title = kwargs.get('window_title')
            
            task = request.env['productivity.task'].browse(task_id)
            
            app_usage = request.env['app.usage.log'].log_app_usage(
                task_id=task.id,
                employee_id=task.employee_id.id,
                app_name=app_name,
                app_path=app_path,
                window_title=window_title,
            )
            
            return {
                'status': 'success',
                'app_usage_id': app_usage.id,
                'message': 'App usage logged'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/productivity/end_app_usage/<int:app_usage_id>', type='json', auth='user', methods=['POST'])
    def end_app_usage(self, app_usage_id, **kwargs):
        """End app usage logging"""
        try:
            app_usage = request.env['app.usage.log'].browse(app_usage_id)
            app_usage.end_app_usage()
            
            return {
                'status': 'success',
                'duration': app_usage.duration,
                'message': 'App usage ended'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/productivity/detect_restricted_app', type='json', auth='user', methods=['POST'])
    def detect_restricted_app(self, **kwargs):
        """Check if detected app is restricted"""
        try:
            app_names = kwargs.get('app_names', [])
            
            config = request.env['productivity.config'].get_config()
            restricted_apps = config.get_restricted_apps_list()
            
            detected_restricted = []
            for app in app_names:
                if any(restricted in app.lower() for restricted in [r.lower() for r in restricted_apps]):
                    detected_restricted.append(app)
            
            return {
                'status': 'success',
                'restricted_detected': detected_restricted,
                'should_pause': len(detected_restricted) > 0,
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/productivity/get_task_summary/<int:task_id>', type='json', auth='user')
    def get_task_summary(self, task_id, **kwargs):
        """Get task summary"""
        try:
            task = request.env['productivity.task'].browse(task_id)
            
            return {
                'status': 'success',
                'task_id': task.id,
                'name': task.name,
                'state': task.state,
                'total_working_time': task.total_working_time,
                'total_paused_time': task.total_paused_time,
                # 'screenshots_count': len(task.screenshot_ids),  # Screenshot functionality removed
                'activities_count': len(task.activity_log_ids),
                'app_usages_count': len(task.app_usage_ids),
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/productivity/get_employee_active_task', type='json', auth='user')
    def get_employee_active_task(self, **kwargs):
        """Get currently active task for employee"""
        try:
            employee = request.env['hr.employee'].search([
                ('user_id', '=', request.env.user.id)
            ], limit=1)
            
            if not employee:
                return {'status': 'error', 'message': 'Employee not found'}
            
            active_task = request.env['productivity.task'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['running', 'paused']),
            ], limit=1)
            
            if active_task:
                return {
                    'status': 'success',
                    'task_id': active_task.id,
                    'name': active_task.name,
                    'state': active_task.state,
                    'total_working_time': active_task.total_working_time,
                }
            else:
                return {'status': 'success', 'task_id': None, 'message': 'No active task'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/productivity/log_away_time', type='json', auth='user', methods=['POST'])
    def log_away_time(self, **kwargs):
        """Log time spent away from Odoo"""
        try:
            task_id = kwargs.get('task_id')
            away_start = kwargs.get('away_start')
            away_end = kwargs.get('away_end')
            duration_seconds = kwargs.get('duration_seconds')
            application_name = kwargs.get('application_name', 'Unknown Application')

            if not task_id:
                return {'status': 'error', 'message': 'Task ID required'}

            task = request.env['productivity.task'].browse(task_id)
            if not task.exists():
                return {'status': 'error', 'message': 'Task not found'}

            # Create activity log for away time
            request.env['activity.log'].create({
                'task_id': task_id,
                'employee_id': task.employee_id.id,
                'activity_type': 'away',
                'start_time': away_start,
                'end_time': away_end,
                'duration': duration_seconds / 3600.0,  # Convert to hours
                'description': f'User was away from Odoo on {application_name}',
                'app_name': application_name,
            })

            # Also log as app usage
            request.env['app.usage.log'].create({
                'task_id': task_id,
                'employee_id': task.employee_id.id,
                'app_name': application_name,
                'app_path': 'External Application',
                'window_title': f'Away from Odoo - {application_name}',
                'start_time': away_start,
                'end_time': away_end,
                'duration': duration_seconds / 3600.0,
                'is_restricted': True,  # Mark as restricted since user left Odoo
            })

            return {
                'status': 'success',
                'message': f'Logged {duration_seconds}s away time',
                'duration': duration_seconds
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/web/productivity/export_report', type='http', auth='user')
    def export_productivity_report(self, employee_id, date_from, date_to, **kwargs):
        """Export productivity report to Excel"""
        try:
            import io
            from datetime import datetime
            
            # Try to import xlsxwriter, fallback to CSV if not available
            try:
                import xlsxwriter
                has_xlsx = True
            except ImportError:
                has_xlsx = False
            
            employee = request.env['hr.employee'].browse(int(employee_id))
            date_from_dt = datetime.strptime(date_from, '%Y-%m-%d').date()
            date_to_dt = datetime.strptime(date_to, '%Y-%m-%d').date()
            
            # Get tasks in date range
            tasks = request.env['productivity.task'].search([
                ('employee_id', '=', employee.id),
                ('start_time', '>=', fields.Datetime.to_string(datetime.combine(date_from_dt, datetime.min.time()))),
                ('start_time', '<=', fields.Datetime.to_string(datetime.combine(date_to_dt, datetime.max.time()))),
            ])
            
            if has_xlsx:
                # Create Excel file
                output = io.BytesIO()
                workbook = xlsxwriter.Workbook(output)
                worksheet = workbook.add_worksheet('Productivity Report')
                
                # Formats
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4472C4',
                    'font_color': 'white',
                    'border': 1
                })
                
                # Write headers
                headers = ['Task Name', 'Start Time', 'Stop Time', 'State', 
                          'Working Hours', 'Paused Hours']  # Screenshot columns removed
                
                for col, header in enumerate(headers):
                    worksheet.write(0, col, header, header_format)
                
                # Write data
                row = 1
                for task in tasks:
                    # productive_ss = len(task.screenshot_ids.filtered(lambda s: s.is_productive))  # Screenshot functionality removed
                    # unproductive_ss = len(task.screenshot_ids.filtered(lambda s: not s.is_productive))  # Screenshot functionality removed
                    
                    worksheet.write(row, 0, task.name or '')
                    worksheet.write(row, 1, str(task.start_time) if task.start_time else '')
                    worksheet.write(row, 2, str(task.stop_time) if task.stop_time else '')
                    worksheet.write(row, 3, task.state or '')
                    worksheet.write(row, 4, round(task.total_working_time, 2))
                    worksheet.write(row, 5, round(task.total_paused_time, 2))
                    # worksheet.write(row, 6, len(task.screenshot_ids))  # Screenshot functionality removed
                    # worksheet.write(row, 7, productive_ss)  # Screenshot functionality removed
                    # worksheet.write(row, 8, unproductive_ss)  # Screenshot functionality removed
                    row += 1
                
                # Add summary section
                row += 2
                worksheet.write(row, 0, 'SUMMARY', header_format)
                row += 1
                worksheet.write(row, 0, 'Total Tasks:')
                worksheet.write(row, 1, len(tasks))
                row += 1
                worksheet.write(row, 0, 'Total Working Hours:')
                worksheet.write(row, 1, round(sum(tasks.mapped('total_working_time')), 2))
                row += 1
                worksheet.write(row, 0, 'Total Paused Hours:')
                worksheet.write(row, 1, round(sum(tasks.mapped('total_paused_time')), 2))
                
                workbook.close()
                output.seek(0)
                
                filename = f'productivity_report_{employee.name}_{date_from}_{date_to}.xlsx'
                
                return request.make_response(
                    output.read(),
                    headers=[
                        ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                        ('Content-Disposition', f'attachment; filename={filename}'),
                    ]
                )
            else:
                # Fallback to CSV
                import csv
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write headers
                writer.writerow(['Task Name', 'Start Time', 'Stop Time', 'State', 
                               'Working Hours', 'Paused Hours'])  # Screenshot columns removed
                
                # Write data
                for task in tasks:
                    # productive_ss = len(task.screenshot_ids.filtered(lambda s: s.is_productive))  # Screenshot functionality removed
                    # unproductive_ss = len(task.screenshot_ids.filtered(lambda s: not s.is_productive))  # Screenshot functionality removed
                    
                    writer.writerow([
                        task.name or '',
                        str(task.start_time) if task.start_time else '',
                        str(task.stop_time) if task.stop_time else '',
                        task.state or '',
                        round(task.total_working_time, 2),
                        round(task.total_paused_time, 2),
                        # len(task.screenshot_ids),  # Screenshot functionality removed
                        # productive_ss,  # Screenshot functionality removed
                        # unproductive_ss  # Screenshot functionality removed
                    ])
                
                filename = f'productivity_report_{employee.name}_{date_from}_{date_to}.csv'
                
                return request.make_response(
                    output.getvalue(),
                    headers=[
                        ('Content-Type', 'text/csv'),
                        ('Content-Disposition', f'attachment; filename={filename}'),
                    ]
                )
                
        except Exception as e:
            return request.make_response(
                f'Error generating report: {str(e)}',
                headers=[('Content-Type', 'text/plain')]
            )

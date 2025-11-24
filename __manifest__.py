{
    'name': 'Employee Productivity Tracker',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Real-time employee productivity tracking with task timers and activity monitoring',
    'description': '''
        A comprehensive module for tracking employee productivity in real-time with:
        - Task-based timers with start/stop functionality
        - System idle detection and automatic pause
        - Entertainment/non-work app detection
        - Real-time activity logging with timestamps
        - Manager dashboard with productivity analytics
        - Export reports (PDF/Excel) for weekly/monthly analysis
    ''',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': ['base', 'hr', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/productivity_task_views.xml',
        # 'views/screenshot_log_views.xml',  # Screenshot functionality removed
        'views/activity_log_views.xml',
        'views/app_usage_log_views.xml',
        'views/manager_dashboard_views.xml',
        'views/productivity_config_views.xml',
        'reports/productivity_report.xml',
        'views/menu_items.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'employee_productivity_tracker/static/src/js/timer_widget.js',
            'employee_productivity_tracker/static/src/js/timer_widget.xml',
            'employee_productivity_tracker/static/src/js/activity_monitor.js',
            'employee_productivity_tracker/static/src/css/timer_widget.css',
            'employee_productivity_tracker/static/src/css/timer_popup.css',
            'employee_productivity_tracker/static/src/css/styles.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

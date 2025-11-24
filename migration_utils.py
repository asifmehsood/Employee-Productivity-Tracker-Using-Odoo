#!/usr/bin/env python3
"""
Productivity Tracker Migration Guide
Helps migrate data from other productivity tracking systems to this Odoo module
"""

from datetime import datetime
import json


class ProductivityDataMigrator:
    """Utility class for migrating productivity data"""
    
    @staticmethod
    def migrate_from_csv(csv_file_path, env):
        """
        Migrate productivity data from CSV file
        
        Expected CSV columns:
        - employee_id, task_name, start_time, stop_time, description
        """
        import csv
        
        tasks_created = 0
        errors = []
        
        try:
            with open(csv_file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    try:
                        # Find employee
                        employee = env['hr.employee'].search([
                            ('id', '=', int(row.get('employee_id')))
                        ], limit=1)
                        
                        if not employee:
                            errors.append(f"Employee {row.get('employee_id')} not found")
                            continue
                        
                        # Create task
                        task = env['productivity.task'].create({
                            'name': row.get('task_name'),
                            'description': row.get('description', ''),
                            'employee_id': employee.id,
                            'start_time': datetime.fromisoformat(row.get('start_time')),
                            'stop_time': datetime.fromisoformat(row.get('stop_time')),
                            'state': 'completed',
                        })
                        
                        tasks_created += 1
                        
                    except Exception as e:
                        errors.append(f"Error processing row {row}: {str(e)}")
        
        except Exception as e:
            errors.append(f"Error reading CSV file: {str(e)}")
        
        return {
            'tasks_created': tasks_created,
            'errors': errors,
        }
    
    @staticmethod
    def migrate_from_json(json_file_path, env):
        """Migrate productivity data from JSON file"""
        tasks_created = 0
        errors = []
        
        try:
            with open(json_file_path, 'r') as jsonfile:
                data = json.load(jsonfile)
                
                if isinstance(data, list):
                    tasks = data
                else:
                    tasks = data.get('tasks', [])
                
                for task_data in tasks:
                    try:
                        employee = env['hr.employee'].search([
                            ('id', '=', task_data.get('employee_id'))
                        ], limit=1)
                        
                        if not employee:
                            errors.append(f"Employee {task_data.get('employee_id')} not found")
                            continue
                        
                        task = env['productivity.task'].create({
                            'name': task_data.get('name'),
                            'description': task_data.get('description', ''),
                            'employee_id': employee.id,
                            'start_time': task_data.get('start_time'),
                            'stop_time': task_data.get('stop_time'),
                            'state': 'completed',
                        })
                        
                        tasks_created += 1
                        
                    except Exception as e:
                        errors.append(f"Error processing task {task_data.get('name')}: {str(e)}")
        
        except Exception as e:
            errors.append(f"Error reading JSON file: {str(e)}")
        
        return {
            'tasks_created': tasks_created,
            'errors': errors,
        }


if __name__ == '__main__':
    print("Productivity Tracker Migration Utility")
    print("This script helps migrate data from other systems to the Odoo module")
    print("\nUsage: Call ProductivityDataMigrator.migrate_from_csv() or migrate_from_json()")

// JavaScript for Timer functionality in Odoo frontend

odoo.define('employee_productivity_tracker.timer', function(require) {
    'use strict';

    var core = require('web.core');
    var Widget = require('web.Widget');
    var ajax = require('web.ajax');
    
    var TimerWidget = Widget.extend({
        template: 'employee_productivity_tracker.timer_widget',
        
        init: function(parent, options) {
            this._super(parent);
            this.task_id = options.task_id;
            this.is_running = options.is_running || false;
            this.elapsed_time = options.elapsed_time || 0;
            this.timer_interval = null;
        },

        willStart: function() {
            var self = this;
            return this._super().then(function() {
                return self._load_task_data();
            });
        },

        start: function() {
            var self = this;
            this.$el.on('click', '.btn-start-timer', function() {
                self.start_timer();
            });
            this.$el.on('click', '.btn-stop-timer', function() {
                self.stop_timer();
            });
            this.$el.on('click', '.btn-pause-timer', function() {
                self.pause_timer();
            });
            this.$el.on('click', '.btn-resume-timer', function() {
                self.resume_timer();
            });
            
            if (this.is_running) {
                this.start_interval();
            }
            
            return this._super();
        },

        _load_task_data: function() {
            var self = this;
            return ajax.jsonrpc('/api/productivity/get_task_summary/' + this.task_id, 'call', {})
                .then(function(result) {
                    if (result.status === 'success') {
                        self.task_data = result;
                        self.is_running = result.state === 'running';
                        self.elapsed_time = result.total_working_time;
                    }
                });
        },

        start_timer: function() {
            var self = this;
            ajax.jsonrpc('/api/productivity/start_task', 'call', {
                task_name: this.$el.find('input[name="task_name"]').val() || 'Task',
                description: this.$el.find('textarea[name="description"]').val() || '',
            }).then(function(result) {
                if (result.status === 'success') {
                    self.task_id = result.task_id;
                    self.is_running = true;
                    self.start_interval();
                    self._refresh_display();
                }
            });
        },

        stop_timer: function() {
            var self = this;
            if (this.timer_interval) {
                clearInterval(this.timer_interval);
            }
            
            ajax.jsonrpc('/api/productivity/stop_task/' + this.task_id, 'call', {})
                .then(function(result) {
                    if (result.status === 'success') {
                        self.is_running = false;
                        self.elapsed_time = result.total_time;
                        self._refresh_display();
                    }
                });
        },

        pause_timer: function() {
            var self = this;
            ajax.jsonrpc('/api/productivity/pause_task/' + this.task_id, 'call', {})
                .then(function(result) {
                    if (result.status === 'success') {
                        self.is_running = false;
                        self._refresh_display();
                    }
                });
        },

        resume_timer: function() {
            var self = this;
            ajax.jsonrpc('/api/productivity/resume_task/' + this.task_id, 'call', {})
                .then(function(result) {
                    if (result.status === 'success') {
                        self.is_running = true;
                        self.start_interval();
                        self._refresh_display();
                    }
                });
        },

        start_interval: function() {
            var self = this;
            if (this.timer_interval) {
                clearInterval(this.timer_interval);
            }
            
            this.timer_interval = setInterval(function() {
                self.elapsed_time += 1 / 3600; // Add 1 second, convert to hours
                self._refresh_display();
            }, 1000);
        },

        _refresh_display: function() {
            var hours = Math.floor(this.elapsed_time);
            var minutes = Math.floor((this.elapsed_time % 1) * 60);
            var seconds = Math.floor((((this.elapsed_time % 1) * 60) % 1) * 60);
            
            var time_display = String(hours).padStart(2, '0') + ':' + 
                             String(minutes).padStart(2, '0') + ':' + 
                             String(seconds).padStart(2, '0');
            
            this.$el.find('.timer-display').text(time_display);
            
            // Update button states
            this.$el.find('.btn-start-timer').toggleClass('hidden', this.is_running);
            this.$el.find('.btn-pause-timer').toggleClass('hidden', !this.is_running);
            this.$el.find('.btn-resume-timer').toggleClass('hidden', this.is_running);
            this.$el.find('.btn-stop-timer').toggleClass('hidden', !this.is_running);
        },

        destroy: function() {
            if (this.timer_interval) {
                clearInterval(this.timer_interval);
            }
            this._super();
        },
    });

    return TimerWidget;
});

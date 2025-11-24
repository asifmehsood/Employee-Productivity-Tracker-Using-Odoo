/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { activityMonitorService } from "./activity_monitor";

export class TimerWidget extends Component {
    static template = "employee_productivity_tracker.TimerWidget";

    setup() {
        this.orm = useService('orm');
        this.notification = useService('notification');
        
        // Try to get activity monitor service, fallback to window global
        try {
            this.activityMonitor = useService('activityMonitor');
            console.log('Activity monitor loaded from service registry');
        } catch (error) {
            console.warn('Activity monitor not in service registry, using window fallback');
            this.activityMonitor = null;
        }
        
        this.state = useState({
            elapsed: 0,
            isRunning: false,
            isPaused: false,
            showStartButton: true,
            stopTime: null
        });

        this.checkInterval = null;
        this.windowBlurHandler = null;
        this.windowFocusHandler = null;

        onMounted(() => {
            console.log('Timer widget mounted');
            this.loadTaskState();
            
            // Note: Odoo form views automatically re-render when record changes
            // No need for manual event listeners - OWL's reactive state handles this
            
            // Start timer interval if already running (handles page reload)
            if (this.state.isRunning) {
                console.log('Timer is running, starting interval...');
                try {
                    this.startTimer();
                    // Resume monitoring only if timer was already running (page reload scenario)
                    const record = this.props.record;
                    const taskId = record?.resId;
                    const monitorService = this.activityMonitor || window.activityMonitorService;
                    console.log('Task ID for monitoring:', taskId);
                    console.log('Activity monitor service available:', !!monitorService);
                    if (taskId && monitorService) {
                        console.log('Resuming activity monitoring after page reload for task:', taskId);
                        // Pass stopTime to preserve auto-stop functionality
                        const stopTime = record.data.stop_time || this.state.stopTime;
                        console.log('Passing stop time to monitor on reload:', stopTime);
                        // Call startMonitoring - it will preserve screen permission flags if already granted
                        monitorService.startMonitoring(taskId, stopTime, true); // true = keepPermissionFlags
                    } else {
                        console.warn('Cannot start monitoring - taskId:', taskId, 'service:', !!monitorService);
                    }
                } catch (error) {
                    console.error('Error in onMounted:', error);
                }
            }
        });

        onWillUnmount(() => {
            this.cleanup();
        });
    }

    async loadTaskState() {
        const record = this.props.record;
        if (!record || !record.data) {
            console.log('Timer widget: No record data available');
            // Show start button by default if no data
            this.state.showStartButton = true;
            this.state.isRunning = false;
            this.state.isPaused = false;
            return;
        }

        const state = record.data.state;
        const startTime = record.data.start_time;
        const stopTime = record.data.stop_time;
        const totalWorkingTime = record.data.total_working_time;

        console.log('Timer widget: Loading task state', {
            state: state,
            startTime: startTime,
            stopTime: stopTime,
            totalWorkingTime: totalWorkingTime,
            showStartButton: state === 'draft',
            isCurrentlyRunning: this.state.isRunning
        });
        
        // Debug: Log all available fields on record.data
        console.log('Available fields on record.data:', Object.keys(record.data));
        console.log('start_time value:', record.data.start_time);
        console.log('start_time type:', typeof record.data.start_time);

        // Don't override if timer is already running (prevents reload from stopping timer)
        if (this.state.isRunning && state === 'running') {
            console.log('Timer already running, skipping state reload');
            return;
        }

        // Set button visibility based on state
        // Show start button ONLY for 'draft' state (new task that hasn't started)
        // For 'completed' state - show timer display with final elapsed time (no start button)
        // For 'stopped' state - allow restart with start button
        const shouldShowStartButton = (state === 'draft' || state === 'stopped');
        
        console.log('Should show start button?', shouldShowStartButton, 'for state:', state);
        
        this.state.showStartButton = shouldShowStartButton;
        this.state.isRunning = (state === 'running');
        this.state.isPaused = (state === 'paused');
        this.state.stopTime = stopTime;

        // Store base elapsed time if not already set (prevents reset on reload)
        let baseElapsed = 0;
        
        // Calculate elapsed time
        if (this.state.isRunning && startTime) {
            // For running tasks with start time: calculate from start time to now
            const start = new Date(startTime);
            const now = new Date();
            baseElapsed = Math.floor((now - start) / 1000);
            console.log('Running task with start_time - elapsed:', baseElapsed, 'seconds');
        } else if ((this.state.isRunning || this.state.isPaused) && totalWorkingTime) {
            // For running/paused tasks without start time: use total_working_time
            // This happens when start_time field is not loaded or on page reload
            baseElapsed = Math.floor(totalWorkingTime * 3600);
            console.log('Running/Paused task without start_time - using total_working_time:', baseElapsed, 'seconds (', totalWorkingTime, 'hours)');
        } else if (state === 'completed' && totalWorkingTime) {
            // For completed tasks: show total working time
            baseElapsed = Math.floor(totalWorkingTime * 3600);
        }
        
        // Always update elapsed time to match the calculated value
        // This ensures timer continues from correct position on reload
        this.state.elapsed = baseElapsed;

        console.log('Timer widget state after load:', {
            showStartButton: this.state.showStartButton,
            isRunning: this.state.isRunning,
            isPaused: this.state.isPaused,
            elapsed: this.state.elapsed,
            state: state
        });
    }

    cleanup() {
        console.log('Timer widget cleanup - clearing intervals');
        
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
        
        if (this.pauseStopTimeCheck) {
            clearInterval(this.pauseStopTimeCheck);
            this.pauseStopTimeCheck = null;
        }
    }

    // Helper method to convert stopTime to string format
    getStopTimeString() {
        if (!this.state.stopTime) return null;
        
        // Check if it's already a string
        if (typeof this.state.stopTime === 'string') {
            console.log('stopTime is already a string:', this.state.stopTime);
            return this.state.stopTime;
        }
        
        // Check if it's a DateTime object with ts property (Odoo format)
        if (this.state.stopTime && typeof this.state.stopTime === 'object') {
            console.log('stopTime is an object:', this.state.stopTime);
            console.log('stopTime.ts value:', this.state.stopTime.ts);
            
            // Odoo DateTime object has 'ts' property with timestamp in MILLISECONDS
            if (this.state.stopTime.ts) {
                const date = new Date(this.state.stopTime.ts); // ts is already in milliseconds
                const isoString = date.toISOString().replace('T', ' ').slice(0, 19);
                console.log('Converted DateTime object to string:', isoString);
                console.log('Parsed date:', date.toISOString());
                return isoString;
            }
            
            // Try to convert object to string directly
            if (this.state.stopTime.toString && this.state.stopTime.toString() !== '[object Object]') {
                const strValue = this.state.stopTime.toString();
                console.log('Converted object toString():', strValue);
                return strValue;
            }
        }
        
        console.error('Unable to convert stopTime to string:', this.state.stopTime);
        return null;
    }

    startTimer() {
        if (this.checkInterval) return;

        console.log('Starting timer interval check. Stop time (raw):', this.state.stopTime, 'Type:', typeof this.state.stopTime);

        // Check stop time if set (with proper timezone handling)
        const stopTimeStr = this.getStopTimeString();
        if (stopTimeStr) {
            // Odoo sends datetime as "YYYY-MM-DD HH:MM:SS" in UTC
            // Convert to ISO format: "YYYY-MM-DDTHH:MM:SSZ"
            const stopTimeISO = stopTimeStr.replace(' ', 'T') + 'Z';
            const stop = new Date(stopTimeISO);
            const now = new Date();
            const diffSeconds = Math.floor((stop - now) / 1000);
            
            console.log('Stop time (UTC):', stopTimeISO);
            console.log('Stop time parsed:', stop.toISOString());
            console.log('Current time:', now.toISOString());
            console.log('Timer will run for', diffSeconds, 'seconds (', Math.floor(diffSeconds / 60), 'minutes)');
            
            // If stop time seems invalid, just clear it and run indefinitely
            if (diffSeconds <= 0) {
                console.warn('Stop time appears to be in the past, clearing it. Timer will run indefinitely.');
                this.state.stopTime = null;
            }
        }

        // Check every second for stop time and update elapsed
        this.checkInterval = setInterval(() => {
            if (!this.state.isRunning) return;

            // Increment elapsed time first
            this.state.elapsed += 1;

            // Check if stop time reached (only after running for at least 3 seconds)
            const intervalStopTimeStr = this.getStopTimeString();
            if (intervalStopTimeStr && this.state.elapsed > 3) {
                const now = new Date();
                // Convert Odoo UTC datetime to JavaScript Date consistently
                const stopTimeStr = intervalStopTimeStr.replace(' ', 'T') + 'Z';
                const stop = new Date(stopTimeStr);
                
                const diffSeconds = Math.floor((stop - now) / 1000);
                
                if (this.state.elapsed % 10 === 0) {
                    console.log('Timer check - Elapsed:', this.state.elapsed, 'seconds, Time remaining:', diffSeconds, 'seconds');
                }
                
                if (diffSeconds <= 0) {
                    console.log('Stop time reached! Auto-stopping timer');
                    this.handleStopTimer();
                    return;
                }
            }
        }, 1000);
    }

    async onStartClick() {
        const record = this.props.record;
        const taskId = record?.resId;
        
        if (!taskId) {
            this.notification.add('Please save the task first', {
                type: 'warning',
                title: 'Productivity Tracker'
            });
            return;
        }

        // Check if stop_time is set and if it's in the future
        const stopTime = record.data.stop_time;
        console.log('Checking stop time before starting timer:', stopTime);
        
        if (stopTime) {
            // Convert stop time to proper format for comparison
            let stopDate;
            if (typeof stopTime === 'string') {
                // Format: "YYYY-MM-DD HH:MM:SS"
                stopDate = new Date(stopTime.replace(' ', 'T') + 'Z');
            } else if (stopTime.ts) {
                // DateTime object with timestamp
                stopDate = new Date(stopTime.ts);
            }
            
            const now = new Date();
            console.log('Stop time:', stopDate?.toISOString());
            console.log('Current time:', now.toISOString());
            
            if (stopDate && stopDate <= now) {
                console.warn('Stop time is in the past! Asking user to set future time.');
                this.notification.add('Stop time must be in the future. Please choose a time after current time.', {
                    type: 'danger',
                    title: 'Invalid Stop Time'
                });
                return;
            }
            console.log('Stop time validation passed. Timer can start.');
        } else {
            console.log('No stop time set, will use default (8 hours from now)');
        }

        try {
            // Call server to start timer
            await this.orm.call('productivity.task', 'action_start_timer', [[taskId]]);
            
            // Reload record to update statusbar from draft to running
            await record.load();
            
            // Reload task to get updated state
            const task = await this.orm.read('productivity.task', [taskId], ['start_time', 'stop_time', 'state']);
            if (task && task.length > 0) {
                this.state.stopTime = task[0].stop_time;
                console.log('Timer started. Stop time:', this.state.stopTime);
            }
            
            // Update widget state
            this.state.isRunning = true;
            this.state.showStartButton = false;
            this.state.elapsed = 0;
            
            // Show success notification
            this.notification.add('Timer Started!', {
                type: 'success',
                title: 'Productivity Tracker'
            });

            console.log('Timer started successfully for task:', taskId);
            
            // Start checking
            this.startTimer();
            
            // Trigger activity monitor
            const monitorService = this.activityMonitor || window.activityMonitorService;
            console.log('Checking activity monitor service availability...');
            console.log('Activity monitor service:', monitorService);
            if (monitorService) {
                console.log('Starting activity monitoring for task:', taskId);
                console.log('Passing stop time to monitor:', this.state.stopTime);
                // Pass stopTime to monitor for automatic stop
                monitorService.startMonitoring(taskId, this.state.stopTime);
                console.log('Activity monitoring started successfully');
            } else {
                console.error('Activity monitor service not available!');
            }
        } catch (error) {
            console.error('Error starting timer:', error);
            this.notification.add('Failed to start timer', {
                type: 'danger',
                title: 'Productivity Tracker'
            });
        }
    }

    async handleStopTimer() {
        const record = this.props.record;
        const taskId = record?.resId;
        
        if (!taskId) return;

        console.log('=== HANDLE STOP TIMER CALLED ===');
        console.log('Call stack:', new Error().stack);

        try {
            await this.orm.call('productivity.task', 'action_stop_timer', [[taskId]]);
            
            console.log('Timer stopped successfully for task:', taskId);
            console.log('Reloading task state from server to get accurate state');
            
            // Reload the full record to get updated state from server
            await record.load();
            
            // Reload task state - will set correct button visibility based on actual state
            await this.loadTaskState();
            
            this.notification.add('Timer Stopped! Task completed.', {
                type: 'success',
                title: 'Productivity Tracker'
            });
            
            // Stop activity monitor
            const monitorService = this.activityMonitor || window.activityMonitorService;
            if (monitorService) {
                monitorService.stopMonitoring();
            }

            // Clear interval
            if (this.checkInterval) {
                clearInterval(this.checkInterval);
                this.checkInterval = null;
            }
        } catch (error) {
            console.error('Error stopping timer:', error);
        }
    }

    async onPauseClick() {
        const record = this.props.record;
        const taskId = record?.resId;
        
        if (!taskId) return;

        try {
            await this.orm.call('productivity.task', 'action_pause_timer', [[taskId]]);
            
            this.state.isRunning = false;
            this.state.isPaused = true;
            
            // Reload record to update statusbar
            await record.load();
            
            // Stop interval
            if (this.checkInterval) {
                clearInterval(this.checkInterval);
                this.checkInterval = null;
            }
            
            // Pause activity monitor
            const monitorService = this.activityMonitor || window.activityMonitorService;
            if (monitorService) {
                monitorService.pauseMonitoring();
            }
            
            // Check stop time periodically even when paused
            console.log('Setting up stop time check for paused state');
            this.pauseStopTimeCheck = setInterval(async () => {
                const currentStopTime = record.data.stop_time || this.state.stopTime;
                if (currentStopTime) {
                    let stopDate;
                    if (typeof currentStopTime === 'string') {
                        stopDate = new Date(currentStopTime.replace(' ', 'T') + 'Z');
                    } else if (currentStopTime.ts) {
                        stopDate = new Date(currentStopTime.ts);
                    }
                    
                    const now = new Date();
                    const secondsRemaining = Math.floor((stopDate - now) / 1000);
                    
                    if (secondsRemaining % 30 === 0) { // Log every 30 seconds
                        console.log('Paused - Stop time check:', secondsRemaining, 'seconds remaining');
                    }
                    
                    if (stopDate && stopDate <= now) {
                        console.log('=== STOP TIME REACHED WHILE PAUSED - AUTO STOPPING ===');
                        clearInterval(this.pauseStopTimeCheck);
                        this.pauseStopTimeCheck = null;
                        await this.handleStopTimer();
                    }
                }
            }, 1000); // Check every second
            
            this.notification.add('Timer Paused', {
                type: 'info',
                title: 'Productivity Tracker'
            });
        } catch (error) {
            console.error('Error pausing timer:', error);
        }
    }

    async onResumeClick() {
        const record = this.props.record;
        const taskId = record?.resId;
        
        if (!taskId) return;

        console.log('=== RESUME TIMER CLICKED ===');
        
        // Validate stop time before resuming
        const stopTime = record.data.stop_time || this.state.stopTime;
        console.log('Checking stop time before resuming:', stopTime);
        
        if (stopTime) {
            let stopDate;
            if (typeof stopTime === 'string') {
                stopDate = new Date(stopTime.replace(' ', 'T') + 'Z');
            } else if (stopTime.ts) {
                stopDate = new Date(stopTime.ts);
            }
            
            const now = new Date();
            console.log('Resume validation - Stop time:', stopDate?.toISOString());
            console.log('Resume validation - Current time:', now.toISOString());
            
            if (stopDate && stopDate <= now) {
                console.warn('Cannot resume - stop time has already passed!');
                this.notification.add('Cannot resume: Stop time has already passed. Please set a new stop time in the future.', {
                    type: 'danger',
                    title: 'Cannot Resume Timer'
                });
                
                // Auto-stop the timer since stop time passed
                console.log('Auto-stopping timer since stop time passed while paused');
                await this.handleStopTimer();
                return;
            }
            console.log('Stop time validation passed. Timer can resume.');
        }

        try {
            await this.orm.call('productivity.task', 'action_resume_timer', [[taskId]]);
            
            this.state.isRunning = true;
            this.state.isPaused = false;
            
            // Reload record to update statusbar
            await record.load();
            
            // Clear pause stop time check if it exists
            if (this.pauseStopTimeCheck) {
                console.log('Clearing pause stop time check interval');
                clearInterval(this.pauseStopTimeCheck);
                this.pauseStopTimeCheck = null;
            }
            
            // Restart interval
            this.startTimer();
            
            // Resume activity monitor with stop time
            const monitorService = this.activityMonitor || window.activityMonitorService;
            if (monitorService) {
                console.log('Resuming activity monitor with stop time:', this.state.stopTime);
                monitorService.resumeMonitoring(this.state.stopTime);
            }
            
            this.notification.add('Timer Resumed', {
                type: 'success',
                title: 'Productivity Tracker'
            });
        } catch (error) {
            console.error('Error resuming timer:', error);
        }
    }

    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }

    get displayValue() {
        return this.formatTime(this.state.elapsed);
    }

    get statusClass() {
        return this.state.isRunning ? 'text-success' : 'text-muted';
    }

    get statusIcon() {
        return this.state.isRunning ? 'fa-play-circle' : 'fa-clock-o';
    }

    get statusText() {
        return this.state.isRunning ? '(Running)' : '';
    }
}

registry.category("fields").add("timer_widget", {
    component: TimerWidget,
});

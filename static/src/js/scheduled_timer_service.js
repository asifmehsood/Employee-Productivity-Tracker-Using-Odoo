/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Scheduled Timer Service
 * Handles automatic timer start/stop based on scheduled times
 * Detects window blur/focus to track time spent on other apps
 */
export const scheduledTimerService = {
    dependencies: ["activityMonitor"],

    start(env, { activityMonitor }) {
        const rpc = env.services.rpc;
        const notification = env.services.notification;
        
        let checkInterval = null;
        let activeTasks = new Map(); // taskId -> task data
        let currentActiveTask = null;
        let windowBlurTime = null;
        let isWindowFocused = true;

        /**
         * Check all scheduled tasks and start/stop as needed
         */
        async function checkScheduledTasks() {
            try {
                const now = new Date();
                
                // Fetch all draft and running tasks
                const tasks = await rpc('/web/dataset/search_read', {
                    model: 'productivity.task',
                    domain: [['state', 'in', ['draft', 'running', 'paused']]],
                    fields: ['id', 'name', 'state', 'start_time', 'stop_time', 'employee_id'],
                });

                for (const task of tasks) {
                    const startTime = task.start_time ? new Date(task.start_time) : null;
                    const stopTime = task.stop_time ? new Date(task.stop_time) : null;

                    // Check if task should start
                    if (task.state === 'draft' && startTime && now >= startTime) {
                        await startTaskTimer(task);
                    }

                    // Check if task should stop
                    if (task.state === 'running' && stopTime && now >= stopTime) {
                        await stopTaskTimer(task);
                    }

                    // Keep track of running tasks
                    if (task.state === 'running') {
                        activeTasks.set(task.id, task);
                        if (!currentActiveTask) {
                            currentActiveTask = task.id;
                        }
                    }
                }
            } catch (error) {
                console.error('Error checking scheduled tasks:', error);
            }
        }

        /**
         * Start a task timer automatically
         */
        async function startTaskTimer(task) {
            try {
                await rpc('/web/dataset/call_button', {
                    model: 'productivity.task',
                    method: 'action_start_timer',
                    args: [[task.id]],
                });

                activeTasks.set(task.id, task);
                currentActiveTask = task.id;

                // Show notification popup
                notification.add(
                    `Timer Started: ${task.name}`,
                    {
                        title: 'Productivity Tracker',
                        type: 'success',
                        sticky: false,
                        className: 'o_timer_notification',
                    }
                );

                console.log(`Timer auto-started for task: ${task.name} (ID: ${task.id})`);

                // Start activity monitoring
                console.log('Starting activity monitor for task:', task.id);
                await activityMonitor.startMonitoring(task.id);

                // Show real-time popup
                showTimerPopup(task);
            } catch (error) {
                console.error('Error starting task timer:', error);
            }
        }

        /**
         * Stop a task timer automatically
         */
        async function stopTaskTimer(task) {
            try {
                await rpc('/web/dataset/call_button', {
                    model: 'productivity.task',
                    method: 'action_stop_timer',
                    args: [[task.id]],
                });

                activeTasks.delete(task.id);
                if (currentActiveTask === task.id) {
                    currentActiveTask = null;
                }

                // Stop activity monitoring
                console.log('Stopping activity monitor');
                activityMonitor.stopMonitoring();

                notification.add(
                    `Timer Stopped: ${task.name}`,
                    {
                        title: 'Productivity Tracker',
                        type: 'info',
                        sticky: false,
                    }
                );

                console.log(`Timer auto-stopped for task: ${task.name} (ID: ${task.id})`);

                // Hide popup
                hideTimerPopup();
            } catch (error) {
                console.error('Error stopping task timer:', error);
            }
        }

        /**
         * Show real-time timer popup
         */
        function showTimerPopup(task) {
            // Remove existing popup if any
            hideTimerPopup();

            const popup = document.createElement('div');
            popup.id = 'timer-popup';
            popup.className = 'timer-popup';
            popup.innerHTML = `
                <div class="timer-popup-content">
                    <div class="timer-popup-header">
                        <span class="timer-popup-icon">⏱️</span>
                        <strong>${task.name}</strong>
                        <button class="timer-popup-close" onclick="this.closest('.timer-popup').remove()">×</button>
                    </div>
                    <div class="timer-popup-body">
                        <div class="timer-popup-time" id="popup-timer-display">00:00:00</div>
                        <div class="timer-popup-status">Running</div>
                    </div>
                </div>
            `;

            document.body.appendChild(popup);

            // Update timer display every second
            updatePopupTimer(task);
        }

        /**
         * Update popup timer display
         */
        function updatePopupTimer(task) {
            const display = document.getElementById('popup-timer-display');
            if (!display) return;

            const startTime = new Date(task.start_time);
            const updateDisplay = () => {
                const now = new Date();
                const elapsed = Math.floor((now - startTime) / 1000);
                
                const hours = Math.floor(elapsed / 3600);
                const minutes = Math.floor((elapsed % 3600) / 60);
                const seconds = elapsed % 60;
                
                display.textContent = 
                    `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            };

            updateDisplay();
            const interval = setInterval(() => {
                if (document.getElementById('popup-timer-display')) {
                    updateDisplay();
                } else {
                    clearInterval(interval);
                }
            }, 1000);
        }

        /**
         * Hide timer popup
         */
        function hideTimerPopup() {
            const popup = document.getElementById('timer-popup');
            if (popup) {
                popup.remove();
            }
        }

        /**
         * Handle window blur (user switched away)
         */
        async function handleWindowBlur() {
            if (!isWindowFocused) return; // Already blurred
            
            isWindowFocused = false;
            windowBlurTime = new Date();

            // Capture current page info before user leaves
            const currentPage = {
                title: document.title,
                url: window.location.href,
                timestamp: windowBlurTime.toISOString()
            };

            console.log('User switched away from Odoo at:', windowBlurTime);
            console.log('Last known location:', currentPage);

            // Pause current task if running
            if (currentActiveTask) {
                try {
                    await rpc('/web/dataset/call_button', {
                        model: 'productivity.task',
                        method: 'action_pause_timer',
                        args: [[currentActiveTask]],
                    });

                    // Log that user left Odoo
                    await rpc('/api/productivity/log_app_usage', {
                        task_id: currentActiveTask,
                        app_name: 'Away from Odoo',
                        app_path: 'External Application',
                        window_title: `Left Odoo at ${windowBlurTime.toLocaleTimeString()}`,
                    });

                    console.log(`Task ${currentActiveTask} paused due to window blur`);
                } catch (error) {
                    console.error('Error pausing task:', error);
                }
            }
        }

        /**
         * Handle window focus (user returned)
         */
        async function handleWindowFocus() {
            if (isWindowFocused) return; // Already focused
            
            isWindowFocused = true;
            const returnTime = new Date();
            
            if (windowBlurTime) {
                const timeAway = Math.floor((returnTime - windowBlurTime) / 1000); // seconds
                console.log(`User returned to Odoo. Time away: ${timeAway} seconds`);

                // Log the away time
                if (currentActiveTask && timeAway > 0) {
                    try {
                        // Get active window title (browser tab title when user left)
                        const awayApp = document.title || 'Unknown Application';
                        
                        await rpc('/api/productivity/log_away_time', {
                            task_id: currentActiveTask,
                            away_start: windowBlurTime.toISOString(),
                            away_end: returnTime.toISOString(),
                            duration_seconds: timeAway,
                            application_name: awayApp,
                        });

                        console.log(`Logged away time: ${timeAway}s on ${awayApp}`);

                        // Resume task
                        await rpc('/web/dataset/call_button', {
                            model: 'productivity.task',
                            method: 'action_resume_timer',
                            args: [[currentActiveTask]],
                        });

                        console.log(`Task ${currentActiveTask} resumed`);
                    } catch (error) {
                        console.error('Error logging away time:', error);
                    }
                }

                windowBlurTime = null;
            }
        }

        /**
         * Initialize service
         */
        function initialize() {
            // Check tasks every 10 seconds
            checkInterval = setInterval(checkScheduledTasks, 10000);
            checkScheduledTasks(); // Initial check

            // Listen for window blur/focus events
            window.addEventListener('blur', handleWindowBlur);
            window.addEventListener('focus', handleWindowFocus);

            // Listen for page visibility changes (for tab switching)
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    handleWindowBlur();
                } else {
                    handleWindowFocus();
                }
            });

            console.log('Scheduled Timer Service initialized');
        }

        /**
         * Cleanup
         */
        function cleanup() {
            if (checkInterval) {
                clearInterval(checkInterval);
            }
            window.removeEventListener('blur', handleWindowBlur);
            window.removeEventListener('focus', handleWindowFocus);
        }

        // Initialize on service start
        initialize();

        return {
            checkScheduledTasks,
            startTaskTimer,
            stopTaskTimer,
            cleanup,
        };
    },
};

registry.category("services").add("scheduledTimer", scheduledTimerService);

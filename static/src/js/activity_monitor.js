/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

/**
 * Activity Monitor Service
 * Monitors user activity, captures screenshots, and tracks application usage
 */
export const activityMonitorService = {
    dependencies: [],

    start(env) {
        let activityCheckInterval = null;
        let currentTaskId = null;
        let lastActiveWindow = null;
        let currentAppUsageId = null;
        let stopTimeCheckInterval = null; // For checking when to stop
        let taskStopTime = null; // Store stop time

        const ACTIVITY_CHECK_INTERVAL = 10 * 1000; // 10 seconds

        /**
         * Detect current browser activity
         */
        async function detectActivity() {
            const info = {
                window: document.title || 'Unknown',
                application: 'Web Browser',
                title: document.title || '',
                url: window.location.href,
            };

            // Detect application type from URL/title
            const url = window.location.href.toLowerCase();
            const title = document.title.toLowerCase();

            if (url.includes('youtube') || title.includes('youtube')) {
                info.application = 'YouTube';
            } else if (url.includes('whatsapp') || title.includes('whatsapp')) {
                info.application = 'WhatsApp';
            } else if (url.includes('facebook') || title.includes('facebook')) {
                info.application = 'Facebook';
            } else if (url.includes('twitter') || title.includes('twitter')) {
                info.application = 'Twitter';
            } else if (url.includes('instagram') || title.includes('instagram')) {
                info.application = 'Instagram';
            } else if (url.includes('github') || title.includes('github')) {
                info.application = 'GitHub';
            } else if (url.includes('stackoverflow') || title.includes('stack overflow')) {
                info.application = 'Stack Overflow';
            } else if (url.includes('gmail') || title.includes('gmail')) {
                info.application = 'Gmail';
            }

            return info;
        }

        /**
         * Log application usage
         */
        async function logAppUsage() {
            console.log('logAppUsage called, currentTaskId:', currentTaskId);
            
            if (!currentTaskId) {
                console.warn('No active task, skipping app usage log');
                return;
            }

            const activityInfo = await detectActivity();
            console.log('Current activity:', activityInfo);
            
            // Check if window changed
            const windowKey = `${activityInfo.application}:${activityInfo.title}`;
            if (lastActiveWindow === windowKey) {
                console.log('Same window, no need to log again');
                return;
            }

            // End previous app usage
            if (currentAppUsageId) {
                try {
                    console.log('Ending previous app usage:', currentAppUsageId);
                    await rpc('/api/productivity/end_app_usage/' + currentAppUsageId, {});
                } catch (error) {
                    console.error('Failed to end app usage:', error);
                }
            }

            // Start new app usage
            try {
                console.log('Logging new app usage:', activityInfo.application);
                const result = await rpc('/api/productivity/log_app_usage', {
                    task_id: currentTaskId,
                    app_name: activityInfo.application,
                    app_path: activityInfo.url,
                    window_title: activityInfo.title,
                });

                console.log('App usage log result:', result);
                if (result.status === 'success') {
                    currentAppUsageId = result.app_usage_id;
                    lastActiveWindow = windowKey;
                }
            } catch (error) {
                console.error('Failed to log app usage:', error);
            }
        }

        /**
         * Start monitoring
         */
        async function startMonitoring(taskId, stopTime = null, keepPermissionFlags = false) {
            console.log('=== START MONITORING CALLED ===');
            console.log('Task ID:', taskId);
            console.log('Stop Time:', stopTime);
            console.log('Current activityCheckInterval:', activityCheckInterval);
            
            if (activityCheckInterval) {
                console.log('Stopping existing monitoring before starting new one');
                stopMonitoring();
            }

            currentTaskId = taskId;
            taskStopTime = stopTime;
            
            console.log(`Activity monitoring started for task ${taskId}`);
            if (taskStopTime) {
                console.log('Will auto-stop monitoring at:', taskStopTime);
                // Set up interval to check stop time every 10 seconds
                stopTimeCheckInterval = setInterval(() => {
                    checkStopTime();
                }, 10000); // Check every 10 seconds
            }
            
            // Set up activity check interval
            activityCheckInterval = setInterval(() => {
                if (currentTaskId === taskId) {
                    logAppUsage();
                }
            }, ACTIVITY_CHECK_INTERVAL);
            
            // Initial activity log
            await logAppUsage();
        }

        /**
         * Check if stop time has been reached
         */
        function checkStopTime() {
            if (!taskStopTime) {
                console.warn('checkStopTime called but taskStopTime is null');
                return;
            }
            
            let stopDate;
            if (typeof taskStopTime === 'string') {
                stopDate = new Date(taskStopTime.replace(' ', 'T') + 'Z');
            } else if (taskStopTime instanceof Date) {
                stopDate = taskStopTime;
            } else if (taskStopTime.ts) {
                stopDate = new Date(taskStopTime.ts);
            } else if (typeof taskStopTime === 'object' && taskStopTime !== null) {
                // Handle DateTime-like objects
                console.warn('taskStopTime is object but not recognized format:', taskStopTime);
                return;
            } else {
                console.error('Unknown taskStopTime format:', typeof taskStopTime, taskStopTime);
                return;
            }
            
            const now = new Date();
            const secondsRemaining = Math.floor((stopDate - now) / 1000);
            
            console.log('Stop time check - Time remaining:', secondsRemaining, 'seconds');
            
            if (secondsRemaining <= 0) {
                console.log('=== STOP TIME REACHED - AUTO STOPPING MONITORING ===');
                // Don't reset permissions - user may reload the page after stop time
                stopMonitoring(false);
            }
        }

        /**
         * Stop monitoring
         * @param {boolean} resetPermissions - Whether to reset screen permission flags (default: true)
         */
        function stopMonitoring(resetPermissions = true) {
            console.log('=== STOPPING MONITORING ===');
            console.log('Reset permissions:', resetPermissions);
            
            if (activityCheckInterval) {
                console.log('Clearing activity check interval');
                clearInterval(activityCheckInterval);
                activityCheckInterval = null;
            }
            
            if (stopTimeCheckInterval) {
                console.log('Clearing stop time check interval');
                clearInterval(stopTimeCheckInterval);
                stopTimeCheckInterval = null;
            }

            // End current app usage
            if (currentAppUsageId) {
                console.log('Ending current app usage:', currentAppUsageId);
                rpc('/api/productivity/end_app_usage/' + currentAppUsageId, {})
                    .catch(error => console.error('Failed to end app usage:', error));
                currentAppUsageId = null;
            }
            
            currentTaskId = null;
            taskStopTime = null;
            lastActiveWindow = null;
            
            console.log('Activity monitoring stopped');
        }

        /**
         * Pause monitoring (when user leaves Odoo)
         */
        function pauseMonitoring() {
            console.log('Pausing activity monitoring');
            
            if (activityCheckInterval) {
                clearInterval(activityCheckInterval);
                activityCheckInterval = null;
            }
            
            // Note: Keep stopTimeCheckInterval running so auto-stop still works when paused

            // End current app usage
            if (currentAppUsageId) {
                rpc('/api/productivity/end_app_usage/' + currentAppUsageId, {})
                    .catch(error => console.error('Failed to end app usage:', error));
                currentAppUsageId = null;
            }
        }

        /**
         * Resume monitoring (when user returns to Odoo)
         */
        function resumeMonitoring(stopTime = null) {
            console.log('Resuming activity monitoring with stop time:', stopTime);
            
            // Note: currentTaskId might not be set if this is called from page reload
            // The monitoring will still work with intervals

            // Update stop time if provided
            if (stopTime) {
                if (typeof stopTime === 'string') {
                    taskStopTime = new Date(stopTime.replace(' ', 'T') + 'Z');
                } else if (stopTime && stopTime.ts) {
                    taskStopTime = new Date(stopTime.ts);
                } else {
                    taskStopTime = stopTime;
                }
                console.log('Updated task stop time on resume:', taskStopTime?.toISOString());
            }

            // Restart screenshot and activity intervals
            screenshotInterval = setInterval(captureScreenshot, SCREENSHOT_INTERVAL);
            activityCheckInterval = setInterval(logAppUsage, ACTIVITY_CHECK_INTERVAL);
            
            // Restart stop time check interval if we have a stop time
            if (taskStopTime) {
                console.log('Restarting stop time check interval on resume');
                stopTimeCheckInterval = setInterval(() => checkStopTime(), 10000);
            }
            
            // Immediate activity check
            logAppUsage();
        }

        /**
         * Check if monitoring is active
         */
        function isMonitoring() {
            return currentTaskId !== null;
        }

        const serviceAPI = {
            startMonitoring,
            stopMonitoring,
            pauseMonitoring,
            resumeMonitoring,
            isMonitoring,
            detectActivity,
        };

        // Export globally for timer widget access
        window.activityMonitorService = serviceAPI;

        return serviceAPI;
    },
};

registry.category("services").add("activityMonitor", activityMonitorService);

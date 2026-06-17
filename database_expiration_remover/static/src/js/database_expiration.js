/**
 * Database Expiration Remover - Main JavaScript
 * This script provides the main functionality for the database expiration remover
 */

(function() {
    'use strict';
    
    console.log("🛡️ Database Expiration Remover loaded");
    
    // Database Expiration Remover Component
    class DatabaseExpirationRemover {
        constructor() {
            this.state = {
                isActive: false,
                trialExtensionDays: 30,
                extensionCount: 0,
                lastExtensionDate: null,
                nextExtensionDate: null,
                databaseExpirationDate: null,
                isExpired: false
            };
            
            this.init();
        }
        
        init() {
            this.loadData();
            this.setupEventListeners();
        }
        
        setupEventListeners() {
            // Add event listeners for any UI interactions
            document.addEventListener('click', (e) => {
                if (e.target.matches('[data-action="extend-trial"]')) {
                    this.extendTrial();
                }
                if (e.target.matches('[data-action="reset-expiration"]')) {
                    this.resetExpiration();
                }
            });
        }
        
        async loadData() {
            try {
                // Load database expiration data via RPC
                const response = await fetch('/web/dataset/call_kw', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        model: "database.expiration.remover",
                        method: "search_read",
                        args: [[]],
                        kwargs: {
                            fields: [
                                "is_active",
                                "trial_extension_days", 
                                "extension_count",
                                "last_extension_date",
                                "next_extension_date",
                                "database_expiration_date",
                                "is_expired"
                            ]
                        }
                    })
                });
                
                const data = await response.json();
                
                if (data && data.result && data.result.length > 0) {
                    const record = data.result[0];
                    this.state.isActive = record.is_active;
                    this.state.trialExtensionDays = record.trial_extension_days;
                    this.state.extensionCount = record.extension_count;
                    this.state.lastExtensionDate = record.last_extension_date;
                    this.state.nextExtensionDate = record.next_extension_date;
                    this.state.databaseExpirationDate = record.database_expiration_date;
                    this.state.isExpired = record.is_expired;
                }
            } catch (error) {
                console.error("Error loading database expiration data:", error);
            }
        }
        
        async extendTrial() {
            try {
                const response = await fetch('/web/dataset/call_kw', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        model: "database.expiration.remover",
                        method: "action_extend_trial",
                        args: [],
                        kwargs: {}
                    })
                });
                
                const result = await response.json();
                
                if (result && result.result) {
                    this.showNotification("Trial Extended", "Trial period extended successfully!", "success");
                    this.loadData(); // Reload data
                }
            } catch (error) {
                console.error("Error extending trial:", error);
                this.showNotification("Error", "Failed to extend trial period", "error");
            }
        }
        
        async resetExpiration() {
            try {
                const response = await fetch('/web/dataset/call_kw', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        model: "database.expiration.remover",
                        method: "action_reset_expiration",
                        args: [],
                        kwargs: {}
                    })
                });
                
                const result = await response.json();
                
                if (result && result.result) {
                    this.showNotification("Expiration Reset", "Expiration date reset successfully!", "success");
                    this.loadData(); // Reload data
                }
            } catch (error) {
                console.error("Error resetting expiration:", error);
                this.showNotification("Error", "Failed to reset expiration date", "error");
            }
        }
        
        showNotification(title, message, type) {
            // Show notification using browser's notification API or console
            console.log(`[${type.toUpperCase()}] ${title}: ${message}`);
            
            // Try to show browser notification if available
            if (Notification.permission === 'granted') {
                new Notification(title, {
                    body: message,
                    icon: '/web/static/img/favicon.ico'
                });
            }
        }
        
        getStatusClass() {
            if (this.state.isExpired) {
                return "status_expired";
            } else if (this.state.databaseExpirationDate) {
                const expirationDate = new Date(this.state.databaseExpirationDate);
                const now = new Date();
                const daysUntilExpiration = Math.ceil((expirationDate - now) / (1000 * 60 * 60 * 24));
                
                if (daysUntilExpiration <= 7) {
                    return "status_warning";
                }
            }
            return "status_active";
        }
        
        formatDate(dateString) {
            if (!dateString) return "N/A";
            const date = new Date(dateString);
            return date.toLocaleDateString() + " " + date.toLocaleTimeString();
        }
        
        getDaysUntilExpiration() {
            if (!this.state.databaseExpirationDate) return "N/A";
            
            const expirationDate = new Date(this.state.databaseExpirationDate);
            const now = new Date();
            const daysUntilExpiration = Math.ceil((expirationDate - now) / (1000 * 60 * 60 * 24));
            
            return daysUntilExpiration;
        }
    }
    
    // Initialize the component when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            new DatabaseExpirationRemover();
        });
    } else {
        new DatabaseExpirationRemover();
    }
    
})();
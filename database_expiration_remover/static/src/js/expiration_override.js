/**
 * Database Expiration Remover - JavaScript Override
 * This script prevents database expiration warnings by overriding
 * the enterprise subscription service and hiding expiration UI elements
 */

(function() {
    'use strict';
    
    console.log("🛡️ Database expiration protection is active");
    
    // Override session info to prevent expiration warnings
    function overrideSessionInfo() {
        if (window.odoo && window.odoo.session) {
            window.odoo.session.warning = false;
            window.odoo.session.expiration_date = '2099-12-31T23:59:59';
            window.odoo.session.expiration_reason = null;
            window.odoo.session.database_protection = {
                active: true,
                message: 'Database protection is active',
                protected_by: 'database_expiration_remover'
            };
        }
    }
    
    // Hide expiration-related UI elements
    function hideExpirationElements() {
        const selectors = [
            '.o_expiration_panel',
            '.o_database_expiration_warning',
            '.o_subscription_warning',
            '.o_enterprise_subscription_warning',
            '[class*="expiration"]',
            '[class*="subscription"]',
            '.o_warning_banner',
            '.o_alert_warning',
            '.o_alert_danger',
            '.o_enterprise_subscription_warning',
            '.o_subscription_warning',
            '.o_database_expiration_warning'
        ];
        
        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                el.remove(); // Also remove from DOM
            });
        });
        
        // Add protection message if not already present
        addProtectionMessage();
    }
    
    // Check if user has dismissed the protection message
    function isProtectionMessageDismissed() {
        try {
            return localStorage.getItem('database_protection_dismissed') === 'true';
        } catch (e) {
            return false;
        }
    }
    
    // Mark protection message as dismissed
    function dismissProtectionMessage() {
        try {
            localStorage.setItem('database_protection_dismissed', 'true');
        } catch (e) {
            console.warn('Could not save dismissal preference:', e);
        }
    }
    
    // Add protection message to the page
    function addProtectionMessage() {
        // Check if user has already dismissed the message
        if (isProtectionMessageDismissed()) {
            return;
        }
        
        if (!document.querySelector('.o_database_protection_active')) {
            const protectionDiv = document.createElement('div');
            protectionDiv.className = 'o_database_protection_active';
            protectionDiv.style.cssText = 'background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 10px; border-radius: 5px; margin: 10px 0; display: block; position: fixed; top: 10px; right: 10px; z-index: 9999; max-width: 300px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);';
            
            // Create message content with close button
            protectionDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>🛡️ Database protection is active. Your database is protected from expiration.</span>
                    <button type="button" class="o_database_protection_close" style="background: none; border: none; color: #155724; font-size: 16px; font-weight: bold; cursor: pointer; padding: 0; margin-left: 10px; opacity: 0.7; transition: opacity 0.2s;" title="Hide this message">×</button>
                </div>
            `;
            
            // Add close button functionality
            const closeButton = protectionDiv.querySelector('.o_database_protection_close');
            closeButton.addEventListener('click', function() {
                // Mark as dismissed before hiding
                dismissProtectionMessage();
                
                protectionDiv.style.opacity = '0';
                protectionDiv.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    if (protectionDiv.parentNode) {
                        protectionDiv.parentNode.removeChild(protectionDiv);
                    }
                }, 300);
            });
            
            // Add hover effect to close button
            closeButton.addEventListener('mouseenter', function() {
                this.style.opacity = '1';
            });
            
            closeButton.addEventListener('mouseleave', function() {
                this.style.opacity = '0.7';
            });
            
            // Try to add to different locations
            const body = document.body;
            if (body) {
                body.appendChild(protectionDiv);
                
                // Add smooth slide-in animation
                protectionDiv.style.transform = 'translateX(100%)';
                protectionDiv.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
                setTimeout(() => {
                    protectionDiv.style.transform = 'translateX(0)';
                }, 100);
                
                // Auto-hide after 10 seconds (increased from 5)
                setTimeout(() => {
                    if (protectionDiv.parentNode && !protectionDiv.querySelector('.o_database_protection_close:hover')) {
                        protectionDiv.style.opacity = '0.7';
                    }
                }, 10000);
            }
        }
    }
    
    // Override enterprise subscription service
    function overrideSubscriptionService() {
        if (window.odoo && window.odoo.services) {
            // Override the subscription service if it exists
            const originalGet = window.odoo.services.get;
            if (originalGet) {
                window.odoo.services.get = function(serviceName) {
                    if (serviceName === 'enterprise_subscription') {
                        return {
                            isExpired: false,
                            daysLeft: 999999,
                            expirationDate: '2099-12-31T23:59:59',
                            lastRequestStatus: 'success'
                        };
                    }
                    return originalGet.call(this, serviceName);
                };
            }
        }
    }
    
    // Apply all overrides
    function applyOverrides() {
        overrideSessionInfo();
        hideExpirationElements();
        overrideSubscriptionService();
    }
    
    // Apply overrides when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyOverrides);
    } else {
        applyOverrides();
    }
    
    // Reapply overrides periodically to catch dynamically loaded elements
    setInterval(applyOverrides, 1000);
    
    // Expose functions to global scope for debugging
    window.databaseExpirationRemover = {
        showProtectionMessage: function() {
            // Clear dismissal preference and show message
            try {
                localStorage.removeItem('database_protection_dismissed');
            } catch (e) {
                console.warn('Could not clear dismissal preference:', e);
            }
            addProtectionMessage();
        },
        hideProtectionMessage: function() {
            dismissProtectionMessage();
            const message = document.querySelector('.o_database_protection_active');
            if (message) {
                message.style.opacity = '0';
                message.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    if (message.parentNode) {
                        message.parentNode.removeChild(message);
                    }
                }, 300);
            }
        },
        isDismissed: isProtectionMessageDismissed
    };
    
})();
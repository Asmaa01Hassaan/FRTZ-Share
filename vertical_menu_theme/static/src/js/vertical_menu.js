///** @odoo-module **/
//
//// Vertical Menu Theme JavaScript - Odoo Enterprise 18 Style
//document.addEventListener('DOMContentLoaded', function() {
//    // Wait for Odoo to load
//    setTimeout(function() {
//        initializeVerticalMenu();
//    }, 1000);
//});
//
//function initializeVerticalMenu() {
//    // Apply vertical menu styles
//    applyVerticalMenuStyles();
//
//    // Add main navbar toggle button
//    addNavbarToggleButton();
//
//    // Add menu interactions
//    addMenuInteractions();
//
//    // Handle responsive menu
//    handleResponsiveMenu();
//
//    // Hide menu on home page
//    hideMenuOnHomePage();
//}
//
//function applyVerticalMenuStyles() {
//    // Find menu sections
//    const menuSections = document.querySelector('.o_menu_sections');
//    if (menuSections) {
//        // Add custom class for styling
//        menuSections.classList.add('vertical-menu-theme');
//
//        // Apply vertical layout with Odoo Enterprise style
//        menuSections.style.display = 'flex';
//        menuSections.style.flexDirection = 'column';
//        menuSections.style.width = '100%';
//        menuSections.style.height = '100%';
//        menuSections.style.overflowY = 'auto';
//        menuSections.style.padding = '0';
//        menuSections.style.background = 'white';
//        menuSections.style.borderRight = '1px solid #dee2e6';
//        menuSections.style.flexGrow = '0';
//        menuSections.style.flexShrink = '0';
//        menuSections.style.position = 'relative';
//        menuSections.style.marginTop = '50px';
//    }
//
//    // Style individual menu sections with Odoo Enterprise style
//    const sections = document.querySelectorAll('.o_menu_section');
//    sections.forEach(section => {
//        section.style.display = 'flex';
//        section.style.flexDirection = 'column';
//        section.style.width = '100%';
//        section.style.marginBottom = '0';
//        section.style.borderBottom = 'none';
//        section.style.paddingBottom = '0';
//        section.style.background = 'transparent';
//    });
//
//    // Style menu items with Odoo Enterprise dashboard style
//    const menuItems = document.querySelectorAll('.o_menu_item');
//    menuItems.forEach(item => {
//        // Add list-group-item classes
//        item.classList.add('list-group-item', 'cursor-pointer', 'border-0', 'd-flex', 'justify-content-between', 'align-items-center');
//
//        item.style.display = 'flex';
//        item.style.alignItems = 'center';
//        item.style.justifyContent = 'space-between';
//        item.style.padding = '8px 16px';
//        item.style.margin = '0';
//        item.style.color = '#495057';
//        item.style.textDecoration = 'none';
//        item.style.borderRadius = '0';
//        item.style.transition = 'all 0.2s ease';
//        item.style.fontSize = '14px';
//        item.style.background = 'transparent';
//        item.style.border = 'none';
//        item.style.width = '100%';
//        item.style.textAlign = 'left';
//        item.style.cursor = 'pointer';
//        item.style.borderBottom = '1px solid #f8f9fa';
//
//        // Wrap text in o_dashboard_name div exactly like dashboard
//        const text = item.textContent.trim();
//        item.innerHTML = `<div class="o_dashboard_name">${text}</div><div xml:space="preserve"></div>`;
//    });
//}
//
//// Removed addToggleButton function - no longer needed
//
//function addNavbarToggleButton() {
//    // Create main navbar toggle button
//    if (!document.querySelector('.o_navbar_toggle')) {
//        const navbarToggleButton = document.createElement('button');
//        navbarToggleButton.className = 'o_navbar_toggle';
//        navbarToggleButton.innerHTML = '<i class="fa fa-fw fa-bars"></i>';
//        navbarToggleButton.title = 'Toggle Top Navigation';
//
//        // Ensure button doesn't interfere with content
//        navbarToggleButton.style.position = 'fixed';
//        navbarToggleButton.style.top = '10px';
//        navbarToggleButton.style.right = '10px';
//        navbarToggleButton.style.zIndex = '1002';
//        navbarToggleButton.style.pointerEvents = 'auto';
//
//        document.body.appendChild(navbarToggleButton);
//
//        // Add click event with dynamic page sizing
//        navbarToggleButton.addEventListener('click', function() {
//            const navbar = document.querySelector('.o_navbar');
//            const body = document.body;
//
//            if (navbar) {
//                navbar.classList.toggle('hidden');
//
//                // Add body classes for dynamic sizing
//                if (navbar.classList.contains('hidden')) {
//                    body.classList.add('navbar-hidden');
//                    body.classList.remove('navbar-visible');
//                } else {
//                    body.classList.add('navbar-visible');
//                    body.classList.remove('navbar-hidden');
//                }
//
//                // Update icon
//                const icon = navbarToggleButton.querySelector('i');
//                if (navbar.classList.contains('hidden')) {
//                    icon.className = 'fa fa-fw fa-eye-slash';
//                    navbarToggleButton.title = 'Show Top Navigation';
//                } else {
//                    icon.className = 'fa fa-fw fa-bars';
//                    navbarToggleButton.title = 'Hide Top Navigation';
//                }
//
//                // Trigger responsive adjustment
//                setTimeout(() => {
//                    handleResponsiveMenu();
//                }, 100);
//            }
//        });
//
//        // Ensure toggle button positioning on view changes
//        ensureToggleButtonPositioning();
//    }
//}
//
//function ensureToggleButtonPositioning() {
//    // Monitor for view changes and ensure toggle button is positioned correctly
//    const observer = new MutationObserver(function(mutations) {
//        mutations.forEach(function(mutation) {
//            if (mutation.type === 'childList') {
//                const toggleButton = document.querySelector('.o_navbar_toggle');
//                if (toggleButton) {
//                    // Ensure button is always positioned correctly
//                    toggleButton.style.position = 'fixed';
//                    toggleButton.style.top = '10px';
//                    toggleButton.style.right = '10px';
//                    toggleButton.style.zIndex = '1002';
//                    toggleButton.style.pointerEvents = 'auto';
//                }
//            }
//        });
//    });
//
//    // Observe changes to the document body
//    observer.observe(document.body, {
//        childList: true,
//        subtree: true
//    });
//}
//
//function addMenuInteractions() {
//    // Add hover effects with Odoo Enterprise style
//    const menuItems = document.querySelectorAll('.o_menu_item');
//    menuItems.forEach(item => {
//        item.addEventListener('mouseenter', function(e) {
//            if (!e.target.classList.contains('active')) {
//                e.target.style.background = 'rgba(0, 0, 0, 0.08)';
//                e.target.style.color = '#111827';
//                e.target.style.transform = 'none';
//                e.target.style.boxShadow = 'none';
//            }
//        });
//
//        item.addEventListener('mouseleave', function(e) {
//            if (!e.target.classList.contains('active')) {
//                e.target.style.background = 'transparent';
//                e.target.style.color = '#495057';
//                e.target.style.transform = 'none';
//                e.target.style.boxShadow = 'none';
//            }
//        });
//    });
//
//    // Add click effects with Odoo Enterprise style
//    menuItems.forEach(item => {
//        item.addEventListener('click', function(e) {
//            // Remove active class from all items
//            menuItems.forEach(i => {
//                i.classList.remove('active');
//                i.style.background = 'transparent';
//                i.style.color = '#495057';
//                i.style.fontWeight = 'normal';
//                i.style.boxShadow = 'none';
//                i.style.borderLeft = 'none';
//            });
//            // Add active class to clicked item
//            e.target.classList.add('active');
//            e.target.style.background = '#e6f2f3';
//            e.target.style.color = '#017e84';
//            e.target.style.fontWeight = '500';
//            e.target.style.borderLeft = '3px solid #017e84';
//            e.target.style.boxShadow = 'none';
//        });
//    });
//}
//
//function handleResponsiveMenu() {
//    // Handle window resize with dynamic page sizing
//    function handleResize() {
//        const navbar = document.querySelector('.o_main_navbar');
//        const content = document.querySelector('.o_main_content');
//        const topNavbar = document.querySelector('.o_navbar');
//        const body = document.body;
//
//        // Check if top navbar is hidden
//        const isTopNavbarHidden = topNavbar && topNavbar.classList.contains('hidden');
//
//        // Set body classes for dynamic sizing
//        if (isTopNavbarHidden) {
//            body.classList.add('navbar-hidden');
//            body.classList.remove('navbar-visible');
//        } else {
//            body.classList.add('navbar-visible');
//            body.classList.remove('navbar-hidden');
//        }
//
//        if (window.innerWidth <= 768) {
//            if (navbar) {
//                navbar.style.width = '240px';
//            }
//            if (content) {
//                content.style.marginLeft = '240px';
//                content.style.width = 'calc(100% - 240px)';
//                content.style.marginTop = isTopNavbarHidden ? '0' : '';
//                content.style.paddingTop = isTopNavbarHidden ? '0' : '';
//            }
//        } else if (window.innerWidth <= 480) {
//            if (navbar) {
//                navbar.style.width = '200px';
//            }
//            if (content) {
//                content.style.marginLeft = '200px';
//                content.style.width = 'calc(100% - 200px)';
//                content.style.marginTop = isTopNavbarHidden ? '0' : '';
//                content.style.paddingTop = isTopNavbarHidden ? '0' : '';
//            }
//        } else {
//            if (navbar) {
//                navbar.style.width = '280px';
//            }
//            if (content) {
//                content.style.marginLeft = '280px';
//                content.style.width = 'calc(100% - 280px)';
//                content.style.marginTop = isTopNavbarHidden ? '0' : '';
//                content.style.paddingTop = isTopNavbarHidden ? '0' : '';
//            }
//        }
//    }
//
//    window.addEventListener('resize', handleResize);
//    handleResize(); // Initial call
//}
//
//function hideMenuOnHomePage() {
//    // Check if we're on the home page
//    function checkHomePage() {
//        const body = document.body;
//        const navbar = document.querySelector('.o_main_navbar');
//
//        if (body.classList.contains('o_home') || window.location.pathname === '/web' || window.location.pathname === '/') {
//            if (navbar) {
//                navbar.style.display = 'none';
//            }
//        } else {
//            if (navbar) {
//                navbar.style.display = 'flex';
//            }
//        }
//    }
//
//    // Check on page load
//    checkHomePage();
//
//    // Check on navigation
//    window.addEventListener('popstate', checkHomePage);
//
//    // Check on URL changes (for SPA navigation)
//    let currentUrl = window.location.href;
//    setInterval(() => {
//        if (window.location.href !== currentUrl) {
//            currentUrl = window.location.href;
//            checkHomePage();
//        }
//    }, 100);
//}


















/** @odoo-module **/
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initializeOverlayMenu, 1500);
});

let currentModule = '';
let isMenuOpen = true;
const MENU_WIDTH = 200;

function initializeOverlayMenu() {
    console.log('🚀 Initializing overlay vertical menu');

    removeExistingMenu();

    createOverlayMenu();

    addOverlayToggleButton();

    updateMenuForCurrentModule();

    setupOverlayListeners();
}

function removeExistingMenu() {
    const oldMenu = document.getElementById('overlayOdooMenu');
    const oldToggle = document.querySelector('.overlay-menu-toggle');

    if (oldMenu) oldMenu.remove();
    if (oldToggle) oldToggle.remove();
}

function createOverlayMenu() {
    const menu = document.createElement('div');
    menu.id = 'overlayOdooMenu';
    menu.className = 'overlay-odoo-menu';

    Object.assign(menu.style, {
        position: 'fixed',
        left: '0',
        top: '100px',
        width: MENU_WIDTH + 'px',
        height: 'calc(100vh - 100px)',
        backgroundColor: 'white',
        boxShadow: '2px 0 10px rgba(0,0,0,0.1)',
        zIndex: '999',
        overflowY: 'auto',
        transition: 'transform 0.3s ease',
        transform: 'translateX(0)'
    });

    document.body.appendChild(menu);

    menu.innerHTML = `
        <div style="padding: 15px; background: #f8f9fa; border-bottom: 1px solid #dee2e6;">
            <div style="font-weight: bold; color: #017e84; font-size: 14px;">Menu</div>
        </div>
        <div style="padding: 20px; text-align: center; color: #6c757d;">
            <i class="fa fa-spinner fa-spin"></i>
            <div style="margin-top: 10px;">Loading...</div>
        </div>
    `;
}

function addOverlayToggleButton() {
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'overlay-menu-toggle';
    toggleBtn.innerHTML = '☰';
    toggleBtn.title = 'Toggle Menu';

    const buttonLeft = isMenuOpen ? (MENU_WIDTH - 30) + 'px' : '10px';

    Object.assign(toggleBtn.style, {
        position: 'fixed',
        top: '50px',
        left: buttonLeft,
        zIndex: '1000',
        backgroundColor: '#017e84',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        width: '30px',
        height: '30px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '14px',
        transition: 'all 0.3s ease'
    });

    document.body.appendChild(toggleBtn);

    toggleBtn.addEventListener('click', function() {
        const menu = document.getElementById('overlayOdooMenu');

        if (isMenuOpen) {
            menu.style.transform = 'translateX(-100%)';
            this.style.left = '10px';
            this.innerHTML = '☰';
            isMenuOpen = false;
        } else {
            menu.style.transform = 'translateX(0)';
            this.style.left = (MENU_WIDTH - 30) + 'px';
            this.innerHTML = '✕';
            isMenuOpen = true;
            updateMenuForCurrentModule();
        }

        adjustContentWithMinimalShift();
    });
}

function detectCurrentModule() {
    const breadcrumbs = document.querySelectorAll('.breadcrumb-item');
    if (breadcrumbs.length >= 2) {
        return breadcrumbs[1].textContent.trim();
    }

    const activeMenu = document.querySelector('.o_menu_item.active');
    if (activeMenu) {
        return activeMenu.textContent.trim();
    }

    const title = document.title;
    if (title.includes('|')) {
        return title.split('|')[0].trim();
    }

    return 'Dashboard';
}

function updateMenuForCurrentModule() {
    const menu = document.getElementById('overlayOdooMenu');
    if (!menu) return;

    const detectedModule = detectCurrentModule();
    console.log('Detected module:', detectedModule);

    if (currentModule !== detectedModule) {
        currentModule = detectedModule;
        const menuItems = getMenuItemsForModule(detectedModule);
        renderMenuContent(menu, detectedModule, menuItems);
    }
}

function getMenuItemsForModule(moduleName) {
    const moduleMenus = {
        'Contacts': [
            {name: 'All Contacts', icon: 'fa-users'},
            {name: 'Companies', icon: 'fa-building'},
            {name: 'Address Book', icon: 'fa-address-book'},
            {name: 'Tags', icon: 'fa-tags'},
            {name: 'Import', icon: 'fa-upload'}
        ],
        'Sales': [
            {name: 'Quotations', icon: 'fa-file-text-o'},
            {name: 'Orders', icon: 'fa-shopping-cart'},
            {name: 'Customers', icon: 'fa-users'},
            {name: 'Products', icon: 'fa-cube'}
        ],
        'Inventory': [
            {name: 'Products', icon: 'fa-cube'},
            {name: 'Stock', icon: 'fa-boxes'},
            {name: 'Transfers', icon: 'fa-exchange-alt'}
        ],
        'CRM': [
            {name: 'Leads', icon: 'fa-star'},
            {name: 'Opportunities', icon: 'fa-bullseye'},
            {name: 'Customers', icon: 'fa-user-circle'}
        ]
    };

    for (const [key, items] of Object.entries(moduleMenus)) {
        if (moduleName.toLowerCase().includes(key.toLowerCase())) {
            return items;
        }
    }

    return [
        {name: 'Dashboard', icon: 'fa-tachometer-alt'},
        {name: 'Records', icon: 'fa-list'},
        {name: 'Reports', icon: 'fa-chart-bar'}
    ];
}

function renderMenuContent(menuElement, moduleName, menuItems) {
    const displayName = moduleName.length > 20 ? moduleName.substring(0, 17) + '...' : moduleName;

    const header = `
        <div style="
            padding: 15px;
            background: #017e84;
            color: white;
            border-bottom: 1px solid #016a6f;
        ">
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fa fa-fw fa-th-large"></i>
                <div style="flex: 1;">
                    <div style="font-weight: bold; font-size: 14px;">${displayName}</div>
                    <div style="font-size: 11px; opacity: 0.9;">Module Menu</div>
                </div>
            </div>
        </div>
    `;

    let itemsHTML = '';
    menuItems.forEach((item, index) => {
        itemsHTML += `
            <a href="#" class="menu-overlay-item" data-item="${item.name}"
               style="
                    display: block;
                    padding: 12px 15px;
                    color: ${index === 0 ? '#017e84' : '#495057'};
                    text-decoration: none;
                    border-bottom: 1px solid #f1f1f1;
                    background: ${index === 0 ? '#e6f2f3' : 'transparent'};
                    transition: all 0.2s;
                    cursor: pointer;
               "
               onmouseover="this.style.background='#f8f9fa'; this.style.color='#017e84'"
               onmouseout="this.style.background='${index === 0 ? '#e6f2f3' : 'transparent'}'; this.style.color='${index === 0 ? '#017e84' : '#495057'}'">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fa fa-fw ${item.icon}" style="width: 20px;"></i>
                    <span>${item.name}</span>
                </div>
            </a>
        `;
    });

    menuElement.innerHTML = header + itemsHTML;

    menuElement.querySelectorAll('.menu-overlay-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const itemName = this.dataset.item;

            menuElement.querySelectorAll('.menu-overlay-item').forEach(i => {
                i.style.background = 'transparent';
                i.style.color = '#495057';
            });

            this.style.background = '#e6f2f3';
            this.style.color = '#017e84';

            showNavigationNotification(itemName);
        });
    });
}

function adjustContentWithMinimalShift() {
    const contentShift = isMenuOpen ? '65px' : '0';

    const contentSelectors = [
        '.o_action_manager',
        '.o_content',
        '.o_view_controller',
        '.o_form_view',
        '.o_list_view',
        '.o_kanban_view',
        '.o_control_panel',
        '.breadcrumb'
    ];

    contentSelectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(element => {
            if (element) {
                if (isMenuOpen) {
                    // تحريك خفيف جداً
                    element.style.marginLeft = contentShift;
                    element.style.transition = 'margin-left 0.3s ease';
                    element.style.boxShadow = '-2px 0 10px rgba(0,0,0,0.05)';
                } else {
                    element.style.marginLeft = '0';
                    element.style.boxShadow = 'none';
                }
                element.style.visibility = 'visible';
                element.style.opacity = '1';
                element.style.position = 'relative';
                element.style.zIndex = '1';
            }
        });
    });
    const buttons = document.querySelectorAll('button');
    buttons.forEach(button => {
        button.style.visibility = 'visible';
        button.style.opacity = '1';
    });
}

function showNavigationNotification(itemName) {
    const notification = document.createElement('div');
    notification.innerHTML = `
        <div style="
            position: fixed;
            top: 70px;
            right: 20px;
            background: #017e84;
            color: white;
            padding: 10px 15px;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 9999;
            animation: slideIn 0.3s ease;
            max-width: 200px;
        ">
            <i class="fa fa-check-circle"></i>
            ${itemName}
        </div>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 2000);
}

function setupOverlayListeners() {
    let lastUrl = window.location.href;
    setInterval(() => {
        if (window.location.href !== lastUrl) {
            lastUrl = window.location.href;
            setTimeout(() => {
                if (isMenuOpen) {
                    updateMenuForCurrentModule();
                }
                adjustContentWithMinimalShift();
            }, 300);
        }
    }, 1000);
    window.addEventListener('resize', adjustContentWithMinimalShift);
}
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }

    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }

    .overlay-odoo-menu {
        box-shadow: 2px 0 15px rgba(0,0,0,0.1) !important;
    }

    .overlay-odoo-menu::-webkit-scrollbar {
        width: 4px;
    }

    .overlay-odoo-menu::-webkit-scrollbar-track {
        background: #f1f1f1;
    }

    .overlay-odoo-menu::-webkit-scrollbar-thumb {
        background: #017e84;
        border-radius: 2px;
    }

    .overlay-menu-toggle:hover {
        background: #016a6f !important;
        transform: scale(1.1);
    }

    .o_main_navbar {
        z-index: 1001 !important;
    }

    @media (max-width: 768px) {
        #overlayOdooMenu {
            width: 180px !important;
        }

        .overlay-menu-toggle {
            left: 150px !important;
            top: 45px !important;
        }
    }
`;
document.head.appendChild(style);

setTimeout(() => {
    initializeOverlayMenu();
}, 2000);




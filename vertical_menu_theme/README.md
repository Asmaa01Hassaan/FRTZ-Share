# Vertical Menu Theme

A custom Odoo theme that transforms the horizontal menu sections into a vertical sidebar layout.

## Features

- **Vertical Menu Layout**: Converts horizontal menu sections to vertical sidebar
- **Responsive Design**: Adapts to different screen sizes
- **Smooth Animations**: Hover effects and transitions
- **Modern Styling**: Clean, professional appearance
- **Custom Colors**: Dark theme with blue accents

## Installation

1. Copy the `vertical_menu_theme` folder to your Odoo addons directory
2. Update the addons list in Odoo
3. Install the module from the Apps menu

## Customization

### Colors
You can customize the colors by editing `static/src/css/vertical_menu.css`:

```css
/* Main background color */
.o_main_navbar {
    background: #2c3e50 !important; /* Change this color */
}

/* Hover color */
.o_menu_item:hover {
    background: #3498db !important; /* Change this color */
}

/* Active item color */
.o_menu_item.active {
    background: #e74c3c !important; /* Change this color */
}
```

### Width
Adjust the menu width by modifying these CSS properties:

```css
.o_main_navbar {
    width: 250px !important; /* Change this value */
}

.o_main_content {
    margin-left: 250px !important; /* Should match navbar width */
    width: calc(100% - 250px) !important;
}
```

## Troubleshooting

### Menu not appearing vertical
1. Clear browser cache
2. Restart Odoo server
3. Check if the module is properly installed

### Styling issues
1. Check browser console for CSS errors
2. Verify the CSS file is loaded
3. Check for conflicting styles

## License

LGPL-3

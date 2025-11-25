/**
 * WhatsApp Server for Wedding Invitations
 * Uses whatsapp-web.js to send messages without Meta API
 * Can be called from n8n via HTTP requests
 */

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const QRCode = require('qrcode');
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

const app = express();
const upload = multer({ dest: 'uploads/' });

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Store client instance
let client = null;
let isReady = false;
let qrCode = null;
let qrCodeImage = null;

/**
 * Initialize WhatsApp Client
 */
function initializeWhatsApp() {
    console.log('Initializing WhatsApp client...');
    
    client = new Client({
        authStrategy: new LocalAuth({
            dataPath: './.wwebjs_auth'
        }),
        puppeteer: {
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        }
    });

    // QR Code generation
    client.on('qr', async (qr) => {
        console.log('QR Code received, scan with your phone');
        qrcode.generate(qr, { small: true });
        qrCode = qr;
        qrCodeImage = null;

        try {
            qrCodeImage = await QRCode.toDataURL(qr, {
                width: 300,
                errorCorrectionLevel: 'M'
            });
        } catch (error) {
            console.error('Error generating QR image:', error);
            qrCodeImage = null;
        }
    });

    // Ready event
    client.on('ready', () => {
        console.log('WhatsApp client is ready!');
        isReady = true;
        qrCode = null;
        qrCodeImage = null;
    });

    // Authentication
    client.on('authenticated', () => {
        console.log('WhatsApp authenticated');
    });

    // Authentication failure
    client.on('auth_failure', (msg) => {
        console.error('Authentication failure:', msg);
        isReady = false;
        qrCodeImage = null;
    });

    // Disconnected
    client.on('disconnected', (reason) => {
        console.log('WhatsApp client disconnected:', reason);
        isReady = false;
        qrCodeImage = null;
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
            console.log('Attempting to reconnect...');
            initializeWhatsApp();
        }, 5000);
    });

    // Initialize
    client.initialize();
}

/**
 * Format phone number to WhatsApp format
 * @param {string} phoneNumber - Phone number in any format
 * @returns {string} - Formatted phone number
 */
function formatPhoneNumber(phoneNumber) {
    // Remove all non-digit characters
    let cleaned = phoneNumber.replace(/\D/g, '');
    
    // If number doesn't start with country code, assume it needs one
    // You can modify this based on your default country code
    if (cleaned.length < 10) {
        return null;
    }
    
    // Ensure it has country code (add + if not present in original)
    // Format: country code + number (e.g., 1234567890 for US)
    return cleaned + '@c.us';
}

/**
 * Send text message
 */
app.post('/api/send-message', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp client is not ready. Please scan QR code first.'
        });
    }

    try {
        const { phoneNumber, message } = req.body;

        if (!phoneNumber || !message) {
            return res.status(400).json({
                success: false,
                error: 'phoneNumber and message are required'
            });
        }

        const formattedNumber = formatPhoneNumber(phoneNumber);
        if (!formattedNumber) {
            return res.status(400).json({
                success: false,
                error: 'Invalid phone number format'
            });
        }

        // Check if number is registered on WhatsApp
        const isRegistered = await client.isRegisteredUser(formattedNumber);
        if (!isRegistered) {
            return res.status(400).json({
                success: false,
                error: 'Phone number is not registered on WhatsApp'
            });
        }

        // Send message
        const result = await client.sendMessage(formattedNumber, message);
        
        res.json({
            success: true,
            messageId: result.id._serialized,
            timestamp: result.timestamp,
            phoneNumber: formattedNumber
        });
    } catch (error) {
        console.error('Error sending message:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Send message with media (image/document)
 */
app.post('/api/send-media', upload.single('media'), async (req, res) => {
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp client is not ready. Please scan QR code first.'
        });
    }

    try {
        const { phoneNumber, message, mediaUrl } = req.body;
        const file = req.file;

        if (!phoneNumber) {
            return res.status(400).json({
                success: false,
                error: 'phoneNumber is required'
            });
        }

        const formattedNumber = formatPhoneNumber(phoneNumber);
        if (!formattedNumber) {
            return res.status(400).json({
                success: false,
                error: 'Invalid phone number format'
            });
        }

        let media = null;

        // If file uploaded
        if (file) {
            media = MessageMedia.fromFilePath(file.path);
            // Clean up uploaded file after sending
            fs.unlinkSync(file.path);
        }
        // If media URL provided
        else if (mediaUrl) {
            media = await MessageMedia.fromUrl(mediaUrl);
        } else {
            return res.status(400).json({
                success: false,
                error: 'Either file upload or mediaUrl is required'
            });
        }

        // Check if number is registered
        const isRegistered = await client.isRegisteredUser(formattedNumber);
        if (!isRegistered) {
            return res.status(400).json({
                success: false,
                error: 'Phone number is not registered on WhatsApp'
            });
        }

        // Send message with media
        const result = await client.sendMessage(formattedNumber, media, {
            caption: message || ''
        });
        
        res.json({
            success: true,
            messageId: result.id._serialized,
            timestamp: result.timestamp,
            phoneNumber: formattedNumber
        });
    } catch (error) {
        console.error('Error sending media:', error);
        if (req.file && fs.existsSync(req.file.path)) {
            fs.unlinkSync(req.file.path);
        }
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Send bulk messages (for wedding invitations)
 */
app.post('/api/send-bulk', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp client is not ready. Please scan QR code first.'
        });
    }

    try {
        const { guests, messageTemplate, delay = 2000 } = req.body;

        if (!guests || !Array.isArray(guests) || guests.length === 0) {
            return res.status(400).json({
                success: false,
                error: 'guests array is required'
            });
        }

        if (!messageTemplate) {
            return res.status(400).json({
                success: false,
                error: 'messageTemplate is required'
            });
        }

        const results = [];
        const errors = [];

        for (let i = 0; i < guests.length; i++) {
            const guest = guests[i];
            const phoneNumber = guest.phoneNumber || guest.phone || guest.number;
            
            if (!phoneNumber) {
                errors.push({
                    guest: guest.name || `Guest ${i + 1}`,
                    error: 'Phone number is missing'
                });
                continue;
            }

            try {
                // Personalize message
                let personalizedMessage = messageTemplate;
                if (guest.name) {
                    personalizedMessage = personalizedMessage.replace(/\{name\}/g, guest.name);
                }
                if (guest.guestName) {
                    personalizedMessage = personalizedMessage.replace(/\{guestName\}/g, guest.guestName);
                }

                const formattedNumber = formatPhoneNumber(phoneNumber);
                if (!formattedNumber) {
                    errors.push({
                        guest: guest.name || phoneNumber,
                        error: 'Invalid phone number format'
                    });
                    continue;
                }

                // Check if registered
                const isRegistered = await client.isRegisteredUser(formattedNumber);
                if (!isRegistered) {
                    errors.push({
                        guest: guest.name || phoneNumber,
                        error: 'Phone number not registered on WhatsApp'
                    });
                    continue;
                }

                // Send message
                const result = await client.sendMessage(formattedNumber, personalizedMessage);
                
                results.push({
                    guest: guest.name || phoneNumber,
                    phoneNumber: formattedNumber,
                    messageId: result.id._serialized,
                    success: true
                });

                // Delay between messages to avoid rate limiting
                if (i < guests.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            } catch (error) {
                errors.push({
                    guest: guest.name || phoneNumber,
                    error: error.message
                });
            }
        }

        res.json({
            success: true,
            total: guests.length,
            sent: results.length,
            failed: errors.length,
            results: results,
            errors: errors
        });
    } catch (error) {
        console.error('Error sending bulk messages:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Get QR code for scanning
 */
app.get('/api/qr-code', (req, res) => {
    if (isReady) {
        return res.json({
            success: true,
            ready: true,
            message: 'WhatsApp is already connected'
        });
    }

    if (qrCode) {
        return res.json({
            success: true,
            ready: false,
            qrCode: qrCode,
            qrCodeImage: qrCodeImage
        });
    }

    res.status(503).json({
        success: false,
        error: 'QR code not available yet. Please wait...'
    });
});

/**
 * Check status
 */
app.get('/api/status', (req, res) => {
    res.json({
        success: true,
        ready: isReady,
        hasQrCode: !!qrCode,
        hasQrImage: !!qrCodeImage
    });
});

/**
 * Logout and reset
 */
app.post('/api/logout', async (req, res) => {
    try {
        if (client) {
            await client.logout();
            await client.destroy();
            client = null;
            isReady = false;
            qrCode = null;
            qrCodeImage = null;
        }
        res.json({
            success: true,
            message: 'Logged out successfully'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`WhatsApp server running on port ${PORT}`);
    console.log(`API endpoints available at http://localhost:${PORT}/api`);
    initializeWhatsApp();
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\nShutting down...');
    if (client) {
        await client.destroy();
    }
    process.exit(0);
});


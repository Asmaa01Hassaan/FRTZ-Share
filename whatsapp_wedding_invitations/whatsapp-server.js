/**
 * WhatsApp Server for Wedding Invitations
 * Uses whatsapp-web.js to send messages without Meta API
 * Can be called from n8n via HTTP requests
 */

const { Client, LocalAuth, MessageMedia, Poll, Buttons } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const QRCode = require('qrcode');
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

const app = express();
// Increase multer file size limit to 10MB
const upload = multer({ 
    dest: 'uploads/',
    limits: { fileSize: 10 * 1024 * 1024 } // 10MB
});

// Middleware
app.use(cors());
// Increase body size limit to 10MB for image uploads
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

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

    // Handle poll votes for RSVP (poll_vote event)
    client.on('poll_vote', async (vote) => {
        try {
            console.log('=== POLL VOTE EVENT RECEIVED ===');
            console.log('Vote data:', JSON.stringify(vote, null, 2));
            
            // Extract phone number from voter (remove @c.us, @lid, or other suffixes)
            let phoneNumber = '';
            if (vote.voter) {
                phoneNumber = vote.voter.includes('@') ? vote.voter.split('@')[0] : vote.voter;
            }
            const selectedOptions = vote.selectedOptions || [];
            
            console.log(`Poll vote from ${vote.voter} (extracted: ${phoneNumber}): ${selectedOptions.map(o => o.name || o).join(', ')}`);
            
            await processPollResponse(phoneNumber, selectedOptions);
        } catch (error) {
            console.error('Error processing poll_vote event:', error);
        }
    });
    
    // Alternative: Listen for message_create which might capture poll responses
    client.on('message_create', async (message) => {
        try {
            // Check if this is a poll update/response
            if (message.type === 'poll_creation' || message.pollName || message._data?.pollName) {
                console.log('=== POLL MESSAGE DETECTED ===');
                console.log('Poll message:', JSON.stringify(message._data, null, 2));
            }
        } catch (error) {
            console.error('Error in message_create handler:', error);
        }
    });
    
    // Helper function to process poll responses
    async function processPollResponse(phoneNumber, selectedOptions) {
        if (!phoneNumber || !selectedOptions || selectedOptions.length === 0) {
            console.log('Invalid poll response data');
            return;
        }
        
        // Determine response based on vote
        let responseType = null;
        const positiveVotes = ['نعم', 'yes', 'سأحضر', 'اكيد', 'confirm', 'نعم، سأحضر', '✅'];
        const negativeVotes = ['لا', 'no', 'اعتذر', 'لن أحضر', 'decline', 'لا، اعتذر', '❌'];
        
        for (const option of selectedOptions) {
            const optionText = typeof option === 'string' ? option : (option.name || option.localizedName || '');
            const optionLower = optionText.toLowerCase();
            
            if (positiveVotes.some(p => optionLower.includes(p.toLowerCase()))) {
                responseType = 'accepted';
                break;
            } else if (negativeVotes.some(n => optionLower.includes(n.toLowerCase()))) {
                responseType = 'declined';
                break;
            }
        }
        
        console.log(`Determined response type: ${responseType}`);
        
        if (responseType) {
            const odooWebhookUrl = process.env.ODOO_WEBHOOK_URL || 'http://172.17.0.1:8018/whatsapp/webhook';
            
            try {
                console.log(`Sending to Odoo webhook: ${odooWebhookUrl}`);
                const response = await fetch(odooWebhookUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            phoneNumber: phoneNumber,
                            message: selectedOptions.map(o => typeof o === 'string' ? o : (o.name || o.localizedName || '')).join(', '),
                            messageId: '',
                            timestamp: Date.now(),
                            isPollVote: true,
                            responseType: responseType
                        }
                    })
                });
                
                const result = await response.json();
                console.log('Odoo webhook response:', JSON.stringify(result, null, 2));
                
                // Extract auto_reply from various JSON-RPC formats
                // Odoo JSON-RPC can return: {jsonrpc: "2.0", result: {...}, id: null}
                // Or direct: {success: true, auto_reply: "..."}
                let autoReply = null;
                
                // Try different paths to find auto_reply
                if (result.result) {
                    // JSON-RPC format: result.result.auto_reply
                    if (result.result.auto_reply) {
                        autoReply = result.result.auto_reply;
                        console.log('✅ Found auto_reply in result.result.auto_reply');
                    } else if (result.result.result && result.result.result.auto_reply) {
                        // Nested JSON-RPC format
                        autoReply = result.result.result.auto_reply;
                        console.log('✅ Found auto_reply in result.result.result.auto_reply');
                    }
                } else if (result.auto_reply) {
                    // Direct format
                    autoReply = result.auto_reply;
                    console.log('✅ Found auto_reply in result.auto_reply');
                }
                
                // Send auto-reply if successful
                if (autoReply && autoReply.trim()) {
                    try {
                        const chatId = phoneNumber + '@c.us';
                        await client.sendMessage(chatId, autoReply);
                        console.log('✅ Sent auto-reply to', phoneNumber, ':', autoReply.substring(0, 50) + '...');
                    } catch (replyError) {
                        console.error('❌ Error sending auto-reply:', replyError.message);
                    }
                } else {
                    console.log('⚠️ No auto-reply in response.');
                    console.log('⚠️ Result structure:', JSON.stringify(result, null, 2));
                    console.log('⚠️ Result keys:', Object.keys(result));
                    if (result.result) {
                        console.log('⚠️ Result.result keys:', Object.keys(result.result));
                    }
                }
                
            } catch (webhookError) {
                console.error('Error calling Odoo webhook:', webhookError.message);
            }
        }
    }

    // Handle incoming messages for RSVP responses
    client.on('message', async (message) => {
        try {
            // Skip group messages
            if (message.from.includes('@g.us')) {
                return;
            }
            
            // Skip status broadcasts (WhatsApp statuses)
            if (message.from === 'status@broadcast') {
                return;
            }
            
            // Get sender phone number (remove @c.us, @lid, or other suffixes)
            // WhatsApp can send: @c.us (contact), @lid (linked device), @g.us (group)
            let phoneNumber = message.from;
            if (phoneNumber.includes('@')) {
                phoneNumber = phoneNumber.split('@')[0];
            }
            
            // Try to get actual phone number from contact info
            let actualPhoneNumber = phoneNumber;
            
            try {
                // Method 1: Try to get contact info using getContact()
                const contact = await message.getContact();
                console.log(`📞 Contact info: number=${contact?.number}, name=${contact?.name}, pushname=${contact?.pushname}`);
                if (contact && contact.number) {
                    // Remove @c.us suffix if present
                    let contactNumber = contact.number;
                    if (contactNumber.includes('@')) {
                        contactNumber = contactNumber.split('@')[0];
                    }
                    console.log(`📞 Contact number extracted: ${contactNumber} (length: ${contactNumber.length})`);
                    // Only use if it looks like a real phone number
                    if (contactNumber.length >= 10 && contactNumber.length <= 15 && /^\d+$/.test(contactNumber)) {
                        actualPhoneNumber = contactNumber;
                        console.log(`✅ Using contact number from getContact(): ${actualPhoneNumber} (from: ${phoneNumber})`);
                    } else {
                        console.log(`⚠️ Contact number ${contactNumber} doesn't look like a valid phone number`);
                    }
                } else {
                    console.log(`⚠️ Contact has no number property`);
                }
            } catch (contactError) {
                console.log(`⚠️ Could not get contact info: ${contactError.message}`);
            }
            
            // Method 2: Try message.getChat() to get chat info
            if (actualPhoneNumber === phoneNumber || phoneNumber.length > 15) {
                try {
                    const chat = await message.getChat();
                    console.log(`💬 Chat info: id=${JSON.stringify(chat.id)}, name=${chat.name}, isGroup=${chat.isGroup}`);
                    
                    // chat.id might be an object with user, _serialized property or a string
                    let chatId = null;
                    if (typeof chat.id === 'string') {
                        chatId = chat.id;
                    } else if (chat.id && chat.id.user) {
                        // Use chat.id.user which contains the actual phone number
                        chatId = chat.id.user;
                        console.log(`📞 Chat ID user: ${chatId}, server: ${chat.id.server}`);
                    } else if (chat.id && typeof chat.id._serialized === 'string') {
                        chatId = chat.id._serialized;
                    } else if (chat.id && typeof chat.id.toString === 'function') {
                        chatId = chat.id.toString();
                    }
                    
                    if (chatId && !chat.isGroup) {
                        // Remove @c.us, @lid, @g.us suffixes
                        if (typeof chatId === 'string' && chatId.includes && chatId.includes('@')) {
                            chatId = chatId.split('@')[0];
                        }
                        // Only use if it looks like a real phone number (not WhatsApp ID)
                        // WhatsApp IDs are usually longer than 15 digits
                        if (chatId && typeof chatId === 'string' && chatId.length >= 10 && chatId.length <= 15 && /^\d+$/.test(chatId)) {
                            actualPhoneNumber = chatId;
                            console.log(`✅ Using phone from getChat(): ${actualPhoneNumber} (from: ${phoneNumber})`);
                        } else {
                            console.log(`⚠️ Chat ID ${chatId} doesn't look like a valid phone number (length: ${chatId ? chatId.length : 'N/A'}, type: ${typeof chatId})`);
                        }
                    } else if (!chatId) {
                        console.log(`⚠️ Chat ID is not a string or object with user/_serialized property`);
                    }
                } catch (chatError) {
                    console.log(`⚠️ Could not get chat info: ${chatError.message}`);
                }
            }
            
            // Method 3: Try message._data.from or message._data.author
            if (actualPhoneNumber === phoneNumber && message._data) {
                try {
                    // Try to get from _data.key.remoteJid or _data.key.participant
                    let dataPhone = message._data.key?.remoteJid || message._data.key?.participant || message._data.from || message._data.author;
                    if (dataPhone) {
                        // Remove @c.us, @lid, @g.us suffixes
                        if (dataPhone.includes('@')) {
                            dataPhone = dataPhone.split('@')[0];
                        }
                        // Only use if it looks like a real phone number (not WhatsApp ID)
                        if (dataPhone.length >= 10 && dataPhone.length <= 15 && /^\d+$/.test(dataPhone)) {
                            actualPhoneNumber = dataPhone;
                            console.log(`✅ Using phone from _data: ${actualPhoneNumber} (from: ${phoneNumber})`);
                        } else {
                            console.log(`⚠️ _data phone ${dataPhone} doesn't look like a valid phone number (length: ${dataPhone.length})`);
                        }
                    }
                } catch (dataError) {
                    console.log(`⚠️ Could not get phone from _data: ${dataError.message}`);
                }
            }
            
            // Method 4: Try message.author if still not found
            if (actualPhoneNumber === phoneNumber && message.author && message.author !== message.from) {
                let authorPhone = message.author;
                if (authorPhone.includes('@')) {
                    authorPhone = authorPhone.split('@')[0];
                }
                // Only use author if it looks like a real phone number (not too long)
                if (authorPhone.length >= 10 && authorPhone.length <= 15 && /^\d+$/.test(authorPhone)) {
                    actualPhoneNumber = authorPhone;
                    console.log(`✅ Using author phone number: ${actualPhoneNumber} (from: ${phoneNumber})`);
                }
            }
            
            // Method 5: Try to get from client.getContactById() if still not found
            if (actualPhoneNumber === phoneNumber && phoneNumber.length > 15) {
                try {
                    const contactId = message.from;
                    console.log(`🔍 Trying getContactById() with ID: ${contactId}`);
                    const contact = await client.getContactById(contactId);
                    console.log(`📞 ContactById info: number=${contact?.number}, name=${contact?.name}, pushname=${contact?.pushname}`);
                    if (contact && contact.number) {
                        let contactNumber = contact.number;
                        if (contactNumber.includes('@')) {
                            contactNumber = contactNumber.split('@')[0];
                        }
                        if (contactNumber.length >= 10 && contactNumber.length <= 15 && /^\d+$/.test(contactNumber)) {
                            actualPhoneNumber = contactNumber;
                            console.log(`✅ Using contact number from getContactById(): ${actualPhoneNumber} (from: ${phoneNumber})`);
                        } else {
                            console.log(`⚠️ ContactById number ${contactNumber} doesn't look like a valid phone number`);
                        }
                    } else {
                        console.log(`⚠️ ContactById has no number property`);
                    }
                } catch (contactByIdError) {
                    console.log(`⚠️ Could not get contact by ID: ${contactByIdError.message}`);
                }
            }
            
            const messageBody = message.body;
            
            console.log(`📨 Received message from ${message.from} (extracted: ${phoneNumber}, actual: ${actualPhoneNumber}): ${messageBody}`);
            console.log(`📋 Message data: _data.from=${message._data?.from}, _data.key.remoteJid=${message._data?.key?.remoteJid}, _data.key.participant=${message._data?.key?.participant}, author=${message.author}, notifyName=${message.notifyName}`);
            if (actualPhoneNumber !== phoneNumber) {
                console.log(`✅ Phone number resolved: ${phoneNumber} → ${actualPhoneNumber}`);
            } else {
                console.log(`⚠️ Could not resolve actual phone number, using: ${actualPhoneNumber}`);
                if (phoneNumber.length > 15) {
                    console.log(`⚠️ This is likely a WhatsApp ID (${phoneNumber.length} digits), not a real phone number. Guest lookup will likely fail.`);
                }
            }
            
            // Get sender name from various sources
            let senderName = '';
            try {
                // Try notifyName first (most reliable)
                senderName = message.notifyName || '';
                
                // Try to get from contact or chat
                if (!senderName) {
                    try {
                        const contact = await message.getContact();
                        senderName = contact?.pushname || contact?.name || '';
                    } catch (e) {}
                }
                
                if (!senderName) {
                    try {
                        const chat = await message.getChat();
                        senderName = chat?.name || '';
                    } catch (e) {}
                }
                
                console.log(`👤 Sender name: "${senderName}"`);
            } catch (nameError) {
                console.log(`⚠️ Could not get sender name: ${nameError.message}`);
            }
            
            // Forward to Odoo webhook for RSVP processing
            // Use HTTP endpoint (more compatible with Odoo 18)
            // Default: localhost:8069 when using --network host
            let odooWebhookUrl = process.env.ODOO_WEBHOOK_URL || 'http://localhost:8069/whatsapp/webhook/http';
            
            // Ensure we're using the HTTP endpoint (append /http if not present)
            if (!odooWebhookUrl.endsWith('/http') && !odooWebhookUrl.endsWith('/test')) {
                odooWebhookUrl = odooWebhookUrl.replace('/whatsapp/webhook', '/whatsapp/webhook/http');
            }
            
            try {
                const response = await fetch(odooWebhookUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            phoneNumber: actualPhoneNumber,  // Use actual phone number
                            message: messageBody,
                            messageId: message.id._serialized,
                            timestamp: message.timestamp,
                            senderName: senderName  // Add sender name for fallback search
                        }
                    })
                });
                
                const result = await response.json();
                console.log('Odoo webhook response:', JSON.stringify(result, null, 2));
                
                // Extract auto_reply from various JSON-RPC formats
                // Odoo JSON-RPC can return: {jsonrpc: "2.0", result: {...}, id: null}
                // Or direct: {success: true, auto_reply: "..."}
                let autoReply = null;
                
                // Try different paths to find auto_reply
                if (result.result) {
                    // JSON-RPC format: result.result.auto_reply
                    if (result.result.auto_reply) {
                        autoReply = result.result.auto_reply;
                        console.log('✅ Found auto_reply in result.result.auto_reply');
                    } else if (result.result.result && result.result.result.auto_reply) {
                        // Nested JSON-RPC format
                        autoReply = result.result.result.auto_reply;
                        console.log('✅ Found auto_reply in result.result.result.auto_reply');
                    }
                } else if (result.auto_reply) {
                    // Direct format
                    autoReply = result.auto_reply;
                    console.log('✅ Found auto_reply in result.auto_reply');
                }
                
                // If Odoo returned an auto-reply message, send it
                if (autoReply && autoReply.trim()) {
                    try {
                        await message.reply(autoReply);
                        console.log('✅ Sent auto-reply to', phoneNumber, ':', autoReply.substring(0, 50) + '...');
                    } catch (replyError) {
                        console.error('❌ Error sending auto-reply:', replyError.message);
                    }
                } else {
                    console.log('⚠️ No auto-reply in response.');
                    console.log('⚠️ Result structure:', JSON.stringify(result, null, 2));
                    console.log('⚠️ Result keys:', Object.keys(result));
                    if (result.result) {
                        console.log('⚠️ Result.result keys:', Object.keys(result.result));
                    }
                }
            } catch (webhookError) {
                console.error('Error calling Odoo webhook:', webhookError.message);
                // Don't throw - continue processing other messages
            }
        } catch (error) {
            console.error('Error processing incoming message:', error);
        }
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
    if (!isReady || !client) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp client is not ready. Please scan QR code first.'
        });
    }
    
    // Verify client is still connected
    try {
        const state = await client.getState();
        if (state !== 'CONNECTED') {
            console.warn(`WhatsApp client state is ${state}, not CONNECTED`);
            return res.status(503).json({
                success: false,
                error: `WhatsApp client is not connected. Current state: ${state}. Please reconnect.`
            });
        }
    } catch (stateError) {
        console.error('Error checking client state:', stateError);
        return res.status(503).json({
            success: false,
            error: 'Cannot verify WhatsApp connection. Please reconnect.'
        });
    }

    try {
        const { phoneNumber, message, mediaUrl, mediaBase64, mediaMimetype, mediaFilename } = req.body;
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
        // If base64 file provided (image, document, etc.)
        else if (mediaBase64) {
            try {
                const mimetype = mediaMimetype || 'application/octet-stream';
                const filename = mediaFilename || 'file';
                
                // Validate base64 string
                if (!mediaBase64 || typeof mediaBase64 !== 'string') {
                    throw new Error('Invalid base64 data');
                }
                
                // Calculate approximate size
                const approxSize = Math.floor(mediaBase64.length * 3 / 4);
                console.log(`Processing base64 file: size≈${approxSize} bytes, mimetype=${mimetype}, filename=${filename}`);
                
                // Always use file method - more reliable with whatsapp-web.js
                // Clean base64 string (remove whitespace, newlines, etc.)
                let cleanBase64 = mediaBase64;
                if (typeof cleanBase64 !== 'string') {
                    cleanBase64 = String(cleanBase64);
                }
                cleanBase64 = cleanBase64.replace(/\s/g, '').trim();
                
                // Log first part for debugging
                console.log(`Received base64: length=${cleanBase64.length}, first 50 chars: ${cleanBase64.substring(0, 50)}...`);
                
                // Validate base64 format
                if (!/^[A-Za-z0-9+/]*={0,2}$/.test(cleanBase64)) {
                    console.error(`Invalid base64 format. First 100 chars: ${cleanBase64.substring(0, 100)}`);
                    throw new Error('Invalid base64 format - contains invalid characters');
                }
                
                // Decode base64 to buffer
                let imageBuffer;
                try {
                    imageBuffer = Buffer.from(cleanBase64, 'base64');
                    console.log(`Decoded base64 to buffer: ${imageBuffer.length} bytes`);
                } catch (decodeError) {
                    console.error(`Base64 decode error: ${decodeError.message}`);
                    throw new Error(`Failed to decode base64: ${decodeError.message}`);
                }
                
                // Verify buffer is not empty
                if (!imageBuffer || imageBuffer.length === 0) {
                    throw new Error('Decoded buffer is empty');
                }
                
                // Check file header for images
                if (mimetype.startsWith('image/')) {
                    const header = imageBuffer.slice(0, 4);
                    const headerHex = header.toString('hex').toUpperCase();
                    const headerBytes = Array.from(header).map(b => '0x' + b.toString(16).padStart(2, '0')).join(' ');
                    console.log(`File header (first 4 bytes): ${headerHex} (${headerBytes})`);
                    
                    // Check for valid image headers
                    const validHeaders = {
                        'FFD8FF': 'JPEG',
                        '89504E47': 'PNG',
                        '47494638': 'GIF',
                        '47494639': 'GIF'
                    };
                    
                    const isValid = Object.keys(validHeaders).some(h => headerHex.startsWith(h));
                    if (!isValid) {
                        console.warn(`WARNING: File header ${headerHex} does NOT match expected image format for ${mimetype}`);
                        console.warn(`First 20 bytes as hex: ${imageBuffer.slice(0, 20).toString('hex')}`);
                        console.warn(`First 20 bytes as ASCII: ${imageBuffer.slice(0, 20).toString('ascii').replace(/[^\x20-\x7E]/g, '.')}`);
                        // Don't throw error - try to send anyway, it might still work
                        console.warn('Will attempt to send anyway...');
                    } else {
                        const imageType = validHeaders[Object.keys(validHeaders).find(h => headerHex.startsWith(h))];
                        console.log(`✓ Valid ${imageType} image detected`);
                    }
                }
                
                const tempDir = path.join(__dirname, 'uploads');
                
                // Ensure uploads directory exists
                if (!fs.existsSync(tempDir)) {
                    fs.mkdirSync(tempDir, { recursive: true });
                }
                
                // Create temporary file with unique name (sanitize filename for filesystem)
                const sanitizedFilename = filename.replace(/[^a-zA-Z0-9._-]/g, '_');
                const tempPath = path.join(tempDir, `temp_${Date.now()}_${Math.random().toString(36).substring(7)}_${sanitizedFilename}`);
                
                // Ensure directory exists and is writable
                if (!fs.existsSync(tempDir)) {
                    fs.mkdirSync(tempDir, { recursive: true });
                }
                
                fs.writeFileSync(tempPath, imageBuffer);
                
                // Verify file was written correctly
                const stats = fs.statSync(tempPath);
                console.log(`Created temp file: ${tempPath} (${stats.size} bytes, expected ${imageBuffer.length} bytes)`);
                
                if (stats.size !== imageBuffer.length) {
                    throw new Error(`File size mismatch: wrote ${stats.size} bytes, expected ${imageBuffer.length} bytes`);
                }
                
                // Wait a bit to ensure file is fully written
                await new Promise(resolve => setTimeout(resolve, 200));
                
                // Verify file is readable and has correct content
                const verifyBuffer = fs.readFileSync(tempPath);
                if (verifyBuffer.length !== imageBuffer.length) {
                    throw new Error(`File verification failed: read ${verifyBuffer.length} bytes, expected ${imageBuffer.length} bytes`);
                }
                
                // Verify file content matches (byte-by-byte comparison for first 100 bytes)
                const sampleSize = Math.min(100, imageBuffer.length);
                if (!verifyBuffer.slice(0, sampleSize).equals(imageBuffer.slice(0, sampleSize))) {
                    throw new Error('File content verification failed: file content does not match original buffer');
                }
                
                // Check if it's a valid image file (for images)
                if (mimetype.startsWith('image/')) {
                    // Verify it's a valid image by checking magic bytes
                    const magicBytes = verifyBuffer.slice(0, 4).toString('hex').toUpperCase();
                    const validImageHeaders = {
                        '89504E47': 'PNG',
                        'FFD8FFE0': 'JPEG',
                        'FFD8FFE1': 'JPEG',
                        'FFD8FFDB': 'JPEG',
                        '47494638': 'GIF',
                        '47494639': 'GIF'
                    };
                    const isValidImage = Object.keys(validImageHeaders).some(header => magicBytes.startsWith(header));
                    if (isValidImage) {
                        const imageType = validImageHeaders[Object.keys(validImageHeaders).find(header => magicBytes.startsWith(header))];
                        console.log(`Valid ${imageType} image detected (magic bytes: ${magicBytes})`);
                    } else {
                        console.warn(`Warning: File may not be a valid image. Magic bytes: ${magicBytes}, mimetype: ${mimetype}`);
                    }
                }
                
                console.log(`File verified: ${verifyBuffer.length} bytes, content matches`);
                
                // Create MessageMedia from file (most reliable method)
                media = MessageMedia.fromFilePath(tempPath);
                
                // Verify media was created correctly
                if (!media || !media.data) {
                    throw new Error('Failed to create MessageMedia from file');
                }
                
                console.log(`MessageMedia created successfully: mimetype=${media.mimetype}, filename=${media.filename}, data length=${media.data.length}`);
                
                // Store temp path for cleanup (don't delete until after successful send)
                req.tempFilePath = tempPath;
            } catch (base64Error) {
                console.error('Error processing base64 image:', base64Error);
                return res.status(400).json({
                    success: false,
                    error: `Error processing base64 image: ${base64Error.message}`
                });
            }
        }
        // If media URL provided
        else if (mediaUrl) {
            media = await MessageMedia.fromUrl(mediaUrl);
        } else {
            return res.status(400).json({
                success: false,
                error: 'Either file upload, mediaBase64, or mediaUrl is required'
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
        console.log(`Sending media message to ${formattedNumber}, media type: ${media.mimetype}`);
        
        // For images, try multiple approaches
        let result = null;
        let lastError = null;
        
        // First attempt: send with caption
        try {
            result = await client.sendMessage(formattedNumber, media, {
                caption: message || ''
            });
            console.log(`Media message sent successfully: ${result.id._serialized}`);
        } catch (sendError1) {
            console.error('First attempt failed:', sendError1.message);
            lastError = sendError1;
            
            // Second attempt: send without caption (sometimes helps with images)
            if (media.mimetype && media.mimetype.startsWith('image/')) {
                try {
                    console.log('Retrying image send without caption...');
                    result = await client.sendMessage(formattedNumber, media);
                    console.log(`Media message sent successfully (without caption): ${result.id._serialized}`);
                } catch (sendError2) {
                    console.error('Second attempt also failed:', sendError2.message);
                    lastError = sendError2;
                    
                    // Third attempt: send as document instead of image
                    try {
                        console.log('Trying to send as document...');
                        // Create a new MessageMedia with document mimetype
                        const docMedia = new MessageMedia(
                            'application/octet-stream',
                            media.data,
                            media.filename || 'file'
                        );
                        result = await client.sendMessage(formattedNumber, docMedia, {
                            caption: message || ''
                        });
                        console.log(`Media sent as document successfully: ${result.id._serialized}`);
                    } catch (sendError3) {
                        console.error('All attempts failed:', sendError3.message);
                        lastError = sendError3;
                    }
                }
            }
        }
        
        if (result) {
            // Clean up temp file after successful send (give WhatsApp time to read it)
            if (req.tempFilePath && fs.existsSync(req.tempFilePath)) {
                setTimeout(() => {
                    try {
                        fs.unlinkSync(req.tempFilePath);
                        console.log(`Cleaned up temp file after successful send: ${req.tempFilePath}`);
                    } catch (cleanupError) {
                        console.error('Error cleaning up temp file:', cleanupError);
                    }
                }, 30000); // 30 seconds delay to ensure WhatsApp has time to read it
            }
            
            res.json({
                success: true,
                messageId: result.id._serialized,
                timestamp: result.timestamp,
                phoneNumber: formattedNumber
            });
        } else {
            // If all attempts failed, try sending text only as fallback
            if (message) {
                console.log('All media attempts failed, sending text-only message as fallback...');
                try {
                    const textResult = await client.sendMessage(formattedNumber, message);
                    return res.json({
                        success: true,
                        messageId: textResult.id._serialized,
                        timestamp: textResult.timestamp,
                        phoneNumber: formattedNumber,
                        warning: 'Media failed to send, but text message was sent successfully'
                    });
                } catch (textError) {
                    console.error('Fallback text message also failed:', textError);
                    throw new Error(`Failed to send media: ${lastError ? lastError.message : 'Unknown error'}. Fallback text also failed: ${textError.message}`);
                }
            }
            throw lastError || new Error('Failed to send media');
        }
    } catch (error) {
        console.error('Error sending media:', error);
        
        // Clean up temp files
        if (req.file && fs.existsSync(req.file.path)) {
            try {
                fs.unlinkSync(req.file.path);
            } catch (unlinkError) {
                console.error('Error cleaning up uploaded file:', unlinkError);
            }
        }
        
        // Clean up temp file created from base64
        if (req.tempFilePath && fs.existsSync(req.tempFilePath)) {
            try {
                fs.unlinkSync(req.tempFilePath);
                console.log(`Cleaned up temp file after error: ${req.tempFilePath}`);
            } catch (unlinkError) {
                console.error('Error cleaning up temp file:', unlinkError);
            }
        }
        
        // Provide more helpful error message
        let errorMessage = error.message || 'Unknown error';
        if (errorMessage.includes('Evaluation failed')) {
            errorMessage = 'Failed to send image. WhatsApp Web may need to be reconnected. Original error: ' + errorMessage;
        }
        
        res.status(500).json({
            success: false,
            error: errorMessage
        });
    }
});

/**
 * Send poll message for RSVP confirmation
 */
app.post('/api/send-poll', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp client is not ready. Please scan QR code first.'
        });
    }

    try {
        const { phoneNumber, question, options, allowMultipleAnswers = false } = req.body;

        if (!phoneNumber) {
            return res.status(400).json({
                success: false,
                error: 'phoneNumber is required'
            });
        }

        if (!question) {
            return res.status(400).json({
                success: false,
                error: 'question is required'
            });
        }

        if (!options || !Array.isArray(options) || options.length < 2) {
            return res.status(400).json({
                success: false,
                error: 'options array with at least 2 options is required'
            });
        }

        const formattedNumber = formatPhoneNumber(phoneNumber);
        if (!formattedNumber) {
            return res.status(400).json({
                success: false,
                error: 'Invalid phone number format'
            });
        }

        console.log(`Sending poll to ${formattedNumber}: "${question}"`);

        // Create poll message
        const poll = new Poll(question, options, {
            allowMultipleAnswers: allowMultipleAnswers
        });

        const result = await client.sendMessage(formattedNumber, poll);
        
        console.log(`Poll sent successfully to ${formattedNumber}`);
        
        res.json({
            success: true,
            messageId: result.id._serialized,
            timestamp: result.timestamp,
            phoneNumber: formattedNumber
        });
    } catch (error) {
        console.error('Error sending poll:', error);
        res.status(500).json({
            success: false,
            error: error.message || 'Failed to send poll'
        });
    }
});

/**
 * Send interactive buttons message (may not work on all WhatsApp versions)
 */
app.post('/api/send-buttons', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp client is not ready. Please scan QR code first.'
        });
    }

    try {
        const { phoneNumber, body, buttons, title, footer } = req.body;

        if (!phoneNumber || !body || !buttons) {
            return res.status(400).json({
                success: false,
                error: 'phoneNumber, body, and buttons are required'
            });
        }

        const formattedNumber = formatPhoneNumber(phoneNumber);
        if (!formattedNumber) {
            return res.status(400).json({
                success: false,
                error: 'Invalid phone number format'
            });
        }

        console.log(`Sending buttons message to ${formattedNumber}`);

        // Create buttons message
        const buttonMessage = new Buttons(body, buttons, title, footer);

        const result = await client.sendMessage(formattedNumber, buttonMessage);
        
        console.log(`Buttons message sent successfully to ${formattedNumber}`);
        
        res.json({
            success: true,
            messageId: result.id._serialized,
            timestamp: result.timestamp,
            phoneNumber: formattedNumber
        });
    } catch (error) {
        console.error('Error sending buttons:', error);
        // Buttons may not work, suggest using poll instead
        res.status(500).json({
            success: false,
            error: error.message || 'Failed to send buttons. Try using /api/send-poll instead.'
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


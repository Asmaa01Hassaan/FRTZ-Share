#!/bin/bash

# Test script for WhatsApp API endpoints
# Make sure the server is running before executing this script

BASE_URL="http://localhost:3000/api"

echo "🧪 Testing WhatsApp API Endpoints"
echo "=================================="
echo ""

# Test 1: Check Status
echo "1️⃣  Testing Status Endpoint..."
curl -s "$BASE_URL/status" | jq .
echo ""
echo ""

# Test 2: Get QR Code (if not connected)
echo "2️⃣  Testing QR Code Endpoint..."
curl -s "$BASE_URL/qr-code" | jq .
echo ""
echo ""

# Test 3: Send Single Message (replace with your test number)
echo "3️⃣  Testing Send Message Endpoint..."
echo "⚠️  Note: Replace phoneNumber with a valid WhatsApp number for testing"
curl -s -X POST "$BASE_URL/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "phoneNumber": "1234567890",
    "message": "Test message from API"
  }' | jq .
echo ""
echo ""

# Test 4: Send Bulk Messages
echo "4️⃣  Testing Bulk Send Endpoint..."
echo "⚠️  Note: Replace phoneNumbers with valid WhatsApp numbers for testing"
curl -s -X POST "$BASE_URL/send-bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "guests": [
      {
        "name": "Test Guest 1",
        "phoneNumber": "1234567890",
        "guestName": "Test1"
      },
      {
        "name": "Test Guest 2",
        "phoneNumber": "0987654321",
        "guestName": "Test2"
      }
    ],
    "messageTemplate": "Dear {name}, This is a test invitation!",
    "delay": 2000
  }' | jq .
echo ""
echo ""

echo "✅ Tests completed!"
echo ""
echo "Note: If you see errors about phone numbers, make sure:"
echo "  1. The server is running and WhatsApp is connected"
echo "  2. You're using valid WhatsApp phone numbers"
echo "  3. The phone numbers are registered on WhatsApp"


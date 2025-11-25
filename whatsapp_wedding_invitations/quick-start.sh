#!/bin/bash

echo "🎉 WhatsApp Wedding Invitations Setup"
echo "======================================"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

echo "✅ Node.js found: $(node --version)"
echo ""

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ npm found: $(npm --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
fi

echo "🚀 Starting WhatsApp server..."
echo ""
echo "📱 IMPORTANT: A QR code will appear in the terminal."
echo "   Scan it with your WhatsApp mobile app to connect."
echo ""
echo "   Steps:"
echo "   1. Open WhatsApp on your phone"
echo "   2. Go to Settings > Linked Devices"
echo "   3. Tap 'Link a Device'"
echo "   4. Scan the QR code shown below"
echo ""
echo "======================================"
echo ""

# Start the server
npm start


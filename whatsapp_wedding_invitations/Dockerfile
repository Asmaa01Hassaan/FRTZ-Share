# syntax=docker/dockerfile:1
FROM node:18-bullseye

# Install system libs needed for Chrome/puppeteer
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates fonts-liberation libappindicator3-1 \
    libatk-bridge2.0-0 libnspr4 libnss3 libxss1 libxtst6 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ENV PUPPETEER_SKIP_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Install Chromium (alternatively install google-chrome-stable)
RUN apt-get update && apt-get install -y chromium \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 3000
CMD ["npm", "start"]






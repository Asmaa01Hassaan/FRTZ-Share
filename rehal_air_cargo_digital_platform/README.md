# Rehal Air Cargo Digital Platform

A complete freight management system for air transport operations.

## Features

### Flight Management
- Create and manage flights with detailed information (origin, destination, dates, times)
- Track flight status (Draft, Scheduled, In Transit, Arrived, Cancelled)
- Automatic spot creation based on total spots configuration

### Spot Management
- Color-coded spot status:
  - **Red (Full)**: Spot is completely full
  - **Orange (Partial)**: Spot has some capacity used but still available
  - **Green (Empty)**: Spot is completely empty and available
- Real-time capacity tracking (used/available)
- Utilization percentage display

### Shipment/Booking System
- Create shipments with shipper and consignee information
- Automatic cost calculation (base rate + weight rate + fuel surcharge)
- Booking validation (must book at least 2 hours before flight departure)
- Tracking number generation
- Shipment status tracking (Draft, Confirmed, In Transit, Delivered, Cancelled)

### Public Web Portal
- Public flight listing page (`/rehal/flights`)
- Flight details page with visual spot status
- Online booking form
- Booking confirmation page
- Real-time availability checking

## Installation

1. Copy this module to your Odoo addons directory
2. Update the apps list in Odoo
3. Install "Rehal Air Cargo Digital Platform" module

## Usage

### Creating a Flight

1. Go to **Rehal Air Cargo > Flights**
2. Click **Create**
3. Fill in flight details:
   - Flight Number (auto-generated)
   - Flight Code
   - Origin and Destination
   - Departure and Arrival dates/times
   - Total number of spots
4. Save - spots will be automatically created

### Booking a Shipment

**Backend:**
1. Go to **Rehal Air Cargo > Shipments**
2. Click **Create**
3. Select flight and spot
4. Fill in shipment details
5. Confirm booking

**Public Website:**
1. Visit `/rehal/flights` on your website
2. Browse available flights
3. Click "View Details" on a flight
4. Click "Book a Spot"
5. Fill in the booking form
6. Submit

### Spot Status Colors

- **Red**: Spot is full (capacity_used >= capacity)
- **Orange**: Spot is partially booked (0 < capacity_used < capacity)
- **Green**: Spot is empty (capacity_used = 0)

## Technical Details

### Models

- `rehal.flight`: Flight management
- `rehal.spot`: Individual spots within a flight
- `rehal.shipment`: Shipment/bookings

### Key Features

- Automatic spot creation on flight creation
- Real-time capacity calculation
- Booking deadline validation (2 hours before departure)
- Color-coded visual status indicators
- Public website integration

## Dependencies

- base
- sale
- account
- stock
- website

## License

LGPL-3


# Rehal Air Cargo Digital Platform - Installation Guide

## Module Overview
A complete freight management system for air transport operations with real-time spot tracking and public booking portal.

## Installation Steps

### 1. Module Location
The module is located at:
```
custom_laft/laft_project/rehal_air_cargo_digital_platform/
```

### 2. Install the Module

**Option A: Via Odoo UI**
1. Go to Apps menu
2. Click "Update Apps List"
3. Search for "Rehal Air Cargo Digital Platform"
4. Click "Install"

**Option B: Via Command Line**
```bash
cd /home/odoo/PycharmProjects/odoo18/odoo18
python3.10 odoo-bin -c odoo.conf -d your_database -u rehal_air_cargo_digital_platform
```

### 3. Module Dependencies
The module depends on:
- `base`
- `sale`
- `account`
- `stock`
- `website`

All dependencies will be installed automatically.

## Features

### 1. Flight Management
- Create flights with departure/arrival details
- Automatic spot creation (configurable number of spots)
- Real-time capacity tracking
- Flight status: Draft → Scheduled → In Transit → Arrived
- Calendar and Kanban views

### 2. Spot Management with Color Coding
- **🟢 Green (Empty)**: Spot is completely available
- **🟠 Orange (Partial)**: Spot is partially filled but has capacity
- **🔴 Red (Full)**: Spot is completely full

### 3. Shipment/Booking System
- Shipper and consignee information
- Automatic cost calculation:
  - Base rate
  - Weight-based rate
  - Fuel surcharge (15%)
- Booking deadline: 2 hours before flight departure
- Tracking number generation
- Full workflow: Draft → Confirmed → In Transit → Delivered

### 4. Public Web Portal
Users can:
- Browse available flights at `/rehal/flights`
- View flight details with visual spot status
- Book spots online
- Receive booking confirmation

## Usage Guide

### Creating Your First Flight

1. **Navigate to Rehal Air Cargo**
   - Go to: Rehal Air Cargo → Flights
   - Click "Create"

2. **Fill in Flight Details**
   - Flight Code: e.g., "RH001"
   - Origin: e.g., "Dubai"
   - Destination: e.g., "Riyadh"
   - Departure Date & Time
   - Arrival Date & Time
   - Total Spots: e.g., 7 (default)

3. **Save**
   - Spots will be automatically created
   - Flight Number will be auto-generated (FLT00001)

4. **Schedule the Flight**
   - Click "Schedule" button
   - Flight becomes available for booking

### Creating a Shipment (Backend)

1. **Navigate to Shipments**
   - Go to: Rehal Air Cargo → Shipments
   - Click "Create"

2. **Select Flight and Spot**
   - Choose a scheduled flight
   - Select an available spot

3. **Enter Details**
   - Shipper information
   - Consignee information
   - Weight (kg)
   - Description

4. **Confirm Booking**
   - Click "Confirm"
   - System validates 2-hour deadline
   - Spot capacity updates automatically
   - Tracking number generated

### Public Booking (Website)

1. **Browse Flights**
   - Visit: `http://your-domain/rehal/flights`
   - View available flights

2. **Select Flight**
   - Click "View Details"
   - See spot status with colors

3. **Book a Spot**
   - Click "Book a Spot"
   - Fill in booking form
   - Submit

4. **Confirmation**
   - Receive booking confirmation
   - Get tracking number

## Important Notes

### Booking Deadline
⚠️ **Bookings must be made at least 2 hours before flight departure**
- System automatically validates this
- Bookings after deadline will be rejected

### Spot Capacity
- Each spot has a capacity (default: 100 kg)
- Multiple shipments can share a spot
- System tracks used vs available capacity
- Visual indicators show status:
  - Empty: 0% used
  - Partial: 1-99% used
  - Full: 100% used

### Cost Calculation
Automatic pricing formula:
```
Base Rate: 50 (fixed)
Weight Rate: weight × 2
Fuel Surcharge: (Base + Weight Rate) × 15%
Total Cost = Base + Weight Rate + Fuel Surcharge
```

## Menu Structure

```
Rehal Air Cargo
├── Flights
├── Spots
└── Shipments
```

## Views Available

### Flights
- **List View**: Overview of all flights
- **Form View**: Detailed flight information
- **Kanban View**: Visual cards by status
- **Calendar View**: Flight schedule

### Spots
- **List View**: Color-coded spot status
- **Form View**: Spot details and shipments

### Shipments
- **List View**: All bookings
- **Form View**: Complete shipment details

## Security

### User Groups
- **Rehal Air Cargo User**: Can view and create
- **Rehal Air Cargo Manager**: Full access
- **Portal Users**: Read-only access to flights, can create bookings

### Record Rules
- Users can manage their own records
- Managers have full access
- Portal users can view and book

## Troubleshooting

### Issue: Cannot install module
**Solution**: Check dependencies are installed
```bash
python3.10 odoo-bin -c odoo.conf -d your_database -i base,sale,account,stock,website
```

### Issue: Spots not created automatically
**Solution**: 
- Check total_spots field is set
- Spots are created on flight save
- Check server logs for errors

### Issue: Cannot book (deadline error)
**Solution**:
- Booking must be at least 2 hours before departure
- Check flight departure_datetime is set correctly
- Ensure system time is correct

### Issue: Spot status not updating
**Solution**:
- Spot capacity updates when shipments are confirmed
- Only confirmed/in-transit shipments count
- Cancelled/draft shipments don't affect capacity

## Support

For issues or questions:
1. Check server logs: `/var/log/odoo/odoo-server.log`
2. Review module README.md
3. Check model constraints and validations

## Technical Details

### Models
- `rehal.flight`: Flight management
- `rehal.spot`: Individual cargo spots
- `rehal.shipment`: Bookings and shipments

### Controllers
- `RehalPublicController`: Web portal routes

### Key Computed Fields
- `available_spots`: Real-time calculation
- `can_book`: Checks 2-hour deadline
- `spot_status_summary`: HTML visualization
- `capacity_available`: Per-spot calculation

## Upgrade Notes

When upgrading the module:
```bash
python3.10 odoo-bin -c odoo.conf -d your_database -u rehal_air_cargo_digital_platform
```

The module is now ready to use! 🚀


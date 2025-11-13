"""
Management command to sync all GroupWalkSlotManager capacities with BookingSettings

Save this as: bookings/management/commands/sync_slot_capacities.py

Usage:
    python manage.py sync_slot_capacities --dry-run  # Preview changes
    python manage.py sync_slot_capacities             # Apply changes
"""

from django.core.management.base import BaseCommand
from home.models import GroupWalkSlotManager, BookingSettings
from datetime import date

class Command(BaseCommand):
    help = 'Sync all GroupWalkSlotManager capacities with global BookingSettings maximum'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get global max
        global_max = BookingSettings.get_settings().max_dogs_per_booking
        
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'SLOT CAPACITY SYNC\n'
            f'{"="*70}\n'
            f'Global maximum from Booking Settings: {global_max} dogs\n'
            f'{"="*70}\n'
        ))
        
        # Find all slot managers
        slot_managers = GroupWalkSlotManager.objects.all().order_by('date')
        
        if not slot_managers.exists():
            self.stdout.write(self.style.WARNING(
                'No GroupWalkSlotManager records found.\n'
            ))
            return
        
        self.stdout.write(f'\nFound {slot_managers.count()} slot manager(s) to check...\n')
        
        updated_count = 0
        changes = []
        
        for slot_manager in slot_managers:

            # Skip past dates
            if slot_manager.date < date.today():
                continue

            slot_changes = []
            original_values = {}
            
            # Check morning slot
            if slot_manager.morning_slot_capacity != global_max:
                original_values['morning'] = slot_manager.morning_slot_capacity
                slot_changes.append(
                    f"  Morning: {slot_manager.morning_slot_capacity} → {global_max}"
                )
                if not dry_run:
                    slot_manager.morning_slot_capacity = global_max
            
            # Check afternoon slot
            if slot_manager.afternoon_slot_capacity != global_max:
                original_values['afternoon'] = slot_manager.afternoon_slot_capacity
                slot_changes.append(
                    f"  Afternoon: {slot_manager.afternoon_slot_capacity} → {global_max}"
                )
                if not dry_run:
                    slot_manager.afternoon_slot_capacity = global_max
            
            # Check evening slot
            if slot_manager.evening_slot_capacity != global_max:
                original_values['evening'] = slot_manager.evening_slot_capacity
                slot_changes.append(
                    f"  Evening: {slot_manager.evening_slot_capacity} → {global_max}"
                )
                if not dry_run:
                    slot_manager.evening_slot_capacity = global_max
            
            if slot_changes:
                updated_count += 1
                
                # Check if this will affect existing bookings
                from django.db.models import Sum, Q
                from home.models import GroupWalk
                
                # Check bookings for this date
                morning_booked = GroupWalk.objects.filter(
                    booking_date=slot_manager.date,
                    time_slot='09:30-11:30',
                    status='confirmed'
                ).aggregate(total=Sum('number_of_dogs'))['total'] or 0
                
                afternoon_booked = GroupWalk.objects.filter(
                    booking_date=slot_manager.date,
                    time_slot='14:00-16:00',
                    status='confirmed'
                ).aggregate(total=Sum('number_of_dogs'))['total'] or 0
                
                evening_booked = GroupWalk.objects.filter(
                    booking_date=slot_manager.date,
                    time_slot='18:00-20:00',
                    status='confirmed'
                ).aggregate(total=Sum('number_of_dogs'))['total'] or 0
                
                # Build change summary
                change_summary = (
                    f"\n📅 {slot_manager.date.strftime('%A, %B %d, %Y')}:\n" + 
                    '\n'.join(slot_changes)
                )
                
                # Add booking status
                booking_info = []
                if 'morning' in original_values:
                    if morning_booked > global_max:
                        booking_info.append(
                            f"     ⚠️  Morning: {morning_booked} dogs booked (OVERBOOKED by {morning_booked - global_max})"
                        )
                    elif morning_booked > 0:
                        booking_info.append(
                            f"     ✅ Morning: {morning_booked}/{global_max} dogs booked"
                        )
                
                if 'afternoon' in original_values:
                    if afternoon_booked > global_max:
                        booking_info.append(
                            f"     ⚠️  Afternoon: {afternoon_booked} dogs booked (OVERBOOKED by {afternoon_booked - global_max})"
                        )
                    elif afternoon_booked > 0:
                        booking_info.append(
                            f"     ✅ Afternoon: {afternoon_booked}/{global_max} dogs booked"
                        )
                
                if 'evening' in original_values:
                    if evening_booked > global_max:
                        booking_info.append(
                            f"     ⚠️  Evening: {evening_booked} dogs booked (OVERBOOKED by {evening_booked - global_max})"
                        )
                    elif evening_booked > 0:
                        booking_info.append(
                            f"     ✅ Evening: {evening_booked}/{global_max} dogs booked"
                        )
                
                if booking_info:
                    change_summary += "\n   Current bookings:\n" + '\n'.join(booking_info)
                
                changes.append(change_summary)
                
                if not dry_run:
                    slot_manager.save()
        
        # Display results
        self.stdout.write('\n' + '='*70)
        
        if changes:
            if dry_run:
                self.stdout.write(self.style.WARNING(
                    'The following changes WOULD be made:\n'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    'The following changes were made:\n'
                ))
            
            for change in changes:
                self.stdout.write(change)
            
            self.stdout.write('\n' + '='*70 + '\n')
            
            if dry_run:
                self.stdout.write(self.style.WARNING(
                    f'🔍 DRY RUN COMPLETE\n'
                    f'   {updated_count} slot manager(s) need updating.\n'
                    f'   Run without --dry-run to apply changes.\n'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'✅ SYNC COMPLETE\n'
                    f'   Successfully updated {updated_count} slot manager(s)!\n'
                ))
        else:
            self.stdout.write(self.style.SUCCESS(
                '\n✅ ALL SYNCHRONIZED\n'
                '   All slot capacities already match global settings!\n'
            ))
        
        self.stdout.write('='*70 + '\n')
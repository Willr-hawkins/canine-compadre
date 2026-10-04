"""
End-to-end timing test for large group-walk multi-bookings.

Run on Render (Shell tab), where the Google credentials live:

    python manage.py check_booking_timeout
    python manage.py check_booking_timeout --walks 60 --limit 15

What it does:
  1. Picks the N furthest-out available slots (so it never competes with real customers).
  2. POSTs a multi-booking for those slots through the real /book/group/ view,
     exactly like the website does — validation, DB save, batched Google Calendar
     inserts, and the success response. Emails are mocked out so nobody gets spammed.
  3. Bulk-deletes the test bookings via the real admin "Delete selected" code path,
     which also deletes the real calendar events.
  4. Rolls back the whole database transaction, so no test bookings are left behind.

PASS means both the booking and the bulk delete finished well inside the gunicorn
worker timeout, and every booking got a calendar event.
"""

import json
import time
from unittest import mock

from django.conf import settings
from django.contrib import admin
from django.core.management.base import BaseCommand
from django.db import transaction
from django.test import Client

from home.calendar_service import GoogleCalendarService
from home.models import GroupWalk


class _Rollback(Exception):
    """Raised at the end to roll back every DB change the test made."""


def _pick_host():
    for host in getattr(settings, 'ALLOWED_HOSTS', []):
        host = host.lstrip('.')
        if host and host != '*':
            return host
    return 'caninecompadre.co.uk'


class Command(BaseCommand):
    help = "Time a large multi-booking end to end to check it stays under the worker timeout."

    def add_arguments(self, parser):
        parser.add_argument('--walks', type=int, default=50, help='Number of walks to book (default 50)')
        parser.add_argument('--limit', type=float, default=20.0,
                            help='Max seconds allowed for booking and for deleting (default 20)')
        parser.add_argument('--path', default='/book/group/', help='Group booking URL (default /book/group/)')

    def handle(self, *args, **opts):
        walks, limit, path = opts['walks'], opts['limit'], opts['path']

        # ── Pre-flight ──
        if GoogleCalendarService().service is None:
            self.stderr.write(self.style.ERROR(
                "Google Calendar service didn't initialise — run this on Render, where "
                "/etc/secrets/google_credentials.json exists."
            ))
            return

        slots = GroupWalk.get_available_slots(days_ahead=180, required_dogs=1)[-walks:]
        if len(slots) < walks:
            self.stdout.write(self.style.WARNING(
                f"Only {len(slots)} free slots available; testing with {len(slots)} walks."
            ))
        if not slots:
            self.stderr.write(self.style.ERROR("No available slots to test with."))
            return

        selected = [{
            'date': s['date'].isoformat(),
            'timeSlot': s['time_slot'],
            'timeDisplay': s['time_display'],
            'dateDisplay': s['date'].strftime('%B %d, %Y'),
        } for s in slots]

        post_data = {
            'selected_slots': json.dumps(selected),
            'is_multi_booking': 'true',
            'customer_name': 'TIMEOUT TEST - ignore',
            'customer_email': 'timeout-test@example.com',
            'customer_phone': '07000000000',
            'customer_address': '1 Test Lane, Braunton',
            'customer_postcode': 'EX33 1AA',
            'number_of_dogs': '1',
            'dog_0_name': 'Testdog',
            'dog_0_breed': 'Test Terrier',
            'dog_0_age': '3',
            'dog_0_good_with_other_dogs': 'on',
            'dog_0_vet_name': 'Test Vets',
            'dog_0_vet_phone': '01271000000',
            'dog_0_vet_address': '1 Vet Street, Barnstaple',
        }

        self.stdout.write(f"Booking {len(selected)} walks via {path} "
                          f"({selected[0]['date']} → {selected[-1]['date']})...")

        booking_ids, booking_secs, delete_secs = [], None, None
        events_created = 0
        result = None

        try:
            with transaction.atomic():
                # ── 1. Book through the real view, with emails mocked ──
                email_patches = []
                try:
                    from home.email_service import EmailService
                    for name in ('send_multi_booking_confirmation', 'send_group_walk_confirmation',
                                 'send_admin_multi_booking_notification', 'send_admin_notification'):
                        if hasattr(EmailService, name):
                            email_patches.append(mock.patch.object(EmailService, name, return_value=True))
                except ImportError:
                    pass

                for p in email_patches:
                    p.start()
                try:
                    client = Client()
                    start = time.monotonic()
                    response = client.post(path, post_data, HTTP_HOST=_pick_host(), secure=True)
                    booking_secs = time.monotonic() - start
                finally:
                    for p in email_patches:
                        p.stop()

                try:
                    result = response.json()
                except ValueError:
                    self.stderr.write(self.style.ERROR(
                        f"Non-JSON response (HTTP {response.status_code}). Check --path and ALLOWED_HOSTS."
                    ))
                    raise _Rollback()

                if not result.get('success'):
                    self.stderr.write(self.style.ERROR(
                        f"Booking failed: {result.get('message')}\n{json.dumps(result.get('errors'), indent=2)}"
                    ))
                    raise _Rollback()

                booking_ids = result['booking_ids']
                events_created = result.get('calendar_events_created', 0)
                self.stdout.write(f"  booked {len(booking_ids)} walks, "
                                  f"{events_created} calendar events, in {booking_secs:.1f}s")

                # ── 2. Bulk delete through the real admin code path ──
                model_admin = admin.site._registry[GroupWalk]
                start = time.monotonic()
                model_admin.delete_queryset(None, GroupWalk.objects.filter(id__in=booking_ids))
                delete_secs = time.monotonic() - start
                booking_ids = []  # events cleaned up
                self.stdout.write(f"  bulk-deleted bookings + calendar events in {delete_secs:.1f}s")

                # ── 3. Roll everything back ──
                raise _Rollback()

        except _Rollback:
            pass
        finally:
            # Safety net: if anything went wrong after events were created, remove them.
            if booking_ids:
                leftover = list(GroupWalk.objects.filter(id__in=booking_ids)
                                .exclude(calendar_event_id__isnull=True)
                                .values_list('calendar_event_id', flat=True))
                if leftover:
                    GoogleCalendarService().delete_events_batch(leftover)
                    self.stdout.write(f"  cleaned up {len(leftover)} leftover calendar events")

        # ── Verdict ──
        if booking_secs is None or result is None or not result.get('success'):
            self.stderr.write(self.style.ERROR("FAIL — booking didn't complete (see above)."))
            return

        problems = []
        if booking_secs > limit:
            problems.append(f"booking took {booking_secs:.1f}s (limit {limit:.0f}s)")
        if delete_secs is not None and delete_secs > limit:
            problems.append(f"bulk delete took {delete_secs:.1f}s (limit {limit:.0f}s)")
        if events_created < result.get('total_bookings', 0):
            problems.append(f"only {events_created}/{result['total_bookings']} calendar events created")

        if problems:
            self.stderr.write(self.style.ERROR("FAIL — " + "; ".join(problems)))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"PASS — {result['total_bookings']} walks booked in {booking_secs:.1f}s and "
                f"deleted in {delete_secs:.1f}s (gunicorn's default timeout is 30s). "
                f"No test data left in the database."
            ))
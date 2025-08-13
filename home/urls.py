from django.urls import path
from . import views, admin_views

urlpatterns = [
    # Main page
    path('', views.home, name='home'),

    # Booking endpoints (AJAX)
    path('book/group/', views.group_walk_booking, name='group_walking_booking'),
    path('book/individual/', views.individual_walk_booking, name='individual_walk_booking'),

    # Calendar/availability endpoints (AJAX)
    path('api/availability/', views.get_availability_calendar, name='get_availability_calendar'),
    path('api/check-slot/', views.check_slot_availability, name='check_slot_availability'),

    # API endpoints
    path('api/group-form/', views.api_group_form_template, name='api_group_form_template'),
    path('api/individual-form/', views.api_individual_form_template, name='api_individual_form_template'),
    path('api/unavailable-dates/', views.get_unavailable_dates, name='get_unavailable_dates'),
    
    # Admin views (separate pages for admin use)
    path('management/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('management/individual-request/<int:request_id>/', views.admin_individual_request_detail, name='admin_individual_request_detail'),
    
    # Unavailable dates management (superuser only)
    path('management/dates/', admin_views.manage_unavailable_dates, name='manage_unavailable_dates'),
    path('management/mark-date-unavailable/', admin_views.mark_date_unavailable, name='mark_date_unavailable'),
    path('management/mark-date-available/', admin_views.mark_date_available, name='mark_date_available'),
    path('management/get-date-info/', admin_views.get_date_info, name='get_date_info'),
    
    # Utility endpoints
    path('health/', views.health_check, name='health_check'),
    path('debug-booking/', views.debug_booking, name='debug_booking'),
]
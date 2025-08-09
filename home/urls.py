from django.urls import path
from . import views

urlpatterns = [
    # Main page
    path('', views.home, name='home'),

    # Booking endpoints (AJAX)
    path('book/group/', views.group_walk_booking, name='group_walking_booking'),
    path('book/individual/', views.individual_walk_booking, name='indicidual_walk_booking'),

    # Calendar/availability endpoints (AJAX)
    path('api/availability/', views.get_availability_calendar, name='get_availability_calendar'),
    path('api/check-slot/', views.check_slot_availability, name='check_slot_availability'),

    # API endpoints
    path('api/group-form/', views.api_group_form_template, name='api_group_form_template'),
    path('api/individual-form/', views.api_individual_form_template, name='api_individual_form_template'),
    
    # Admin views (separate pages for admin use)
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/individual-request/<int:request_id>/', views.admin_individual_request_detail, name='admin_individual_request_detail'),
    
    # Utility endpoints
    path('health/', views.health_check, name='health_check'),
]
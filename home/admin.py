from django.contrib import admin
from .models import GroupWalk, IndividualWalk, Dog

@admin.register(GroupWalk)
class GroupWalkAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'booking_date', 'time_slot', 'number_of_dogs', 'status', 'created_at']
    list_filter = ['booking_date', 'time_slot', 'status']
    search_fields = ['customer_name', 'customer_email']

@admin.register(IndividualWalk)
class IndividualWalkAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'preferred_date', 'preferred_time', 'status', 'created_at']
    list_filter = ['status', 'preferred_date']
    search_fields = ['customer_name', 'customer_email']

@admin.register(Dog)
class DogAdmin(admin.ModelAdmin):
    list_display = ['name', 'breed', 'age', 'get_booking_customer']
    
    def get_booking_customer(self, obj):
        if obj.group_walk:
            return f"{obj.group_walk.customer_name} (Group)"
        elif obj.individual_walk:
            return f"{obj.individual_walk.customer_name} (Individual)"
        return "No booking"
    get_booking_customer.short_description = 'Customer'
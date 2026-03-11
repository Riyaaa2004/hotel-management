from rest_framework.throttling import UserRateThrottle


class BookingThrottle(UserRateThrottle):
    scope = 'booking'
from django.urls import path

from .views import ReservationAPIView, ReservationListAPIView, ReservationDetailAPIView, CheckInAPIView, \
    CheckOutAPIView, RoomAvailabilityAPIView, HotelOccupancyAPIView, MostBookedRoomsAPIView, RevenueAPIView

urlpatterns = [
    path('reserve/', ReservationAPIView.as_view()),
    path('reservations/', ReservationListAPIView.as_view()),
    path('reservations/<int:pk>/', ReservationDetailAPIView.as_view()),
    path('reservations/<int:pk>/check-in/',CheckInAPIView.as_view()),
    path('reservations/<int:pk>/check-out/',CheckOutAPIView.as_view()),
    path('availability/', RoomAvailabilityAPIView.as_view()),
    path('hotels/<int:hotel_id>/occupancy/', HotelOccupancyAPIView.as_view()),
    path('most-booked-rooms/', MostBookedRoomsAPIView.as_view()),
    path('revenue/', RevenueAPIView.as_view()),


]
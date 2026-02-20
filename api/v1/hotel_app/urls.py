from django.urls import path

from .views import ReservationAPIView, ReservationListAPIView, ReservationDetailAPIView, CheckInAPIView, CheckOutAPIView

urlpatterns = [
    path('reserve/', ReservationAPIView.as_view()),
    path('reservations/', ReservationListAPIView.as_view()),
    path('reservations/<int:pk>/', ReservationDetailAPIView.as_view()),
    path('reservations/<int:pk>/check-in/',CheckInAPIView.as_view()),
    path('reservations/<int:pk>/check-out/',CheckOutAPIView.as_view()),



]
from django.urls import path

from api.v1.accounts.views import RegisterAPIView, AdminApproveReservationAPIView

urlpatterns = [
    path('register/', RegisterAPIView.as_view()),
    path('admin/reservations/<int:pk>/',AdminApproveReservationAPIView.as_view())

]
from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView

from api.v1.accounts.views import RegisterAPIView, AdminApproveReservationAPIView

urlpatterns = [
    path('register/', RegisterAPIView.as_view()),
    path('admin/reservations/<int:pk>/',AdminApproveReservationAPIView.as_view()),
    path('logout/', TokenBlacklistView.as_view(), name='token_blacklist'),

]
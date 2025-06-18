from django.urls import path
from .views import UsuarioCreateView, CustomTokenObtainPairView, CuentaCreateView

urlpatterns = [
    path('users/create/', UsuarioCreateView.as_view(), name='crear-usuario'),
    path('users/login/', CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path('cuentas/crear/', CuentaCreateView.as_view(), name='crear-cuenta')
]

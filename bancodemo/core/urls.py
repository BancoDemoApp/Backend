from django.urls import path
from .views import (
    UsuarioCreateView,
    CustomTokenObtainPairView,
    CuentaCreateView,
    TransaccionCreateView,
    MisCuentasView,
    TransferenciaView,
    TransaccionListView,
    ClienteListView,
    LogListView,
    CancelarTransaccionView,
    BuscarClienteView,
    BuscarCuentaView,
    ReporteTransaccionesView,
    PerfilClienteAPIView,
    ActualizarContrasenaView,
    LogoutView
)

urlpatterns = [
    # ----------------------------
    # AUTENTICACIÓN Y REGISTRO
    # ----------------------------
    path('users/create/', UsuarioCreateView.as_view(), name='crear_usuario'),
    path('users/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # ----------------------------
    # VISTAS PARA CLIENTES
    # ----------------------------
    path('cuentas/mis-cuentas/', MisCuentasView.as_view(), name='mis_cuentas'),
    path('transacciones/transferir/', TransferenciaView.as_view(), name='transferencia'),
    path('mi-perfil/',PerfilClienteAPIView.as_view(), name="mi_perfil"),

    # ----------------------------
    # VISTAS PARA OPERADORES
    # ----------------------------
    path('cuentas/crear/', CuentaCreateView.as_view(), name='crear_cuenta'),
    path('clientes/listar/', ClienteListView.as_view(), name='listar_clientes'),
    path('clientes/buscar/', BuscarClienteView.as_view(), name='buscar_cliente'),
    path('cuentas/buscar/', BuscarCuentaView.as_view(), name='buscar_cuenta'),
    path('logs/listar/', LogListView.as_view(), name='listar_logs'),
    path('transacciones/cancelar/<int:pk>/', CancelarTransaccionView.as_view(), name='cancelar_transaccion'),
    path('transacciones/reporte/', ReporteTransaccionesView.as_view(), name='reporte_transacciones'),

    # ----------------------------
    # VISTAS COMPARTIDAS
    # ----------------------------
    path('transacciones/', TransaccionListView.as_view(), name='lista_transacciones'),
    path('transacciones/crear/', TransaccionCreateView.as_view(), name='crear_transaccion'),
    path('usuarios/cambiar-contrasena/', ActualizarContrasenaView.as_view(), name='cambiar_contrasena'),
]

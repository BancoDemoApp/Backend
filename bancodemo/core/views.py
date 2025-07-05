from rest_framework import generics, permissions, serializers, filters, status
from .models import Usuario, Cuenta, Transaccion, Log
from .serializers import UsuarioSerializer, CuentaSerializer, TransaccionSerializer, CuentaDetalleSerializer, UsuarioPerfilSerializer, ActualizarContrasenaSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from .permissions import EsOperador
from django.contrib.auth import authenticate
from django.db.models import Q
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class UsuarioCreateView(generics.CreateAPIView):
    """
    Endpoint para registrar un nuevo usuario.

    Crea un usuario nuevo (cliente u operador) proporcionando los campos requeridos:
    - nombre
    - correo_electronico
    - password
    - tipo

    Este endpoint no requiere autenticación.
    """
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    
        
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Endpoint para iniciar sesión con autenticación JWT.

    Requiere:
    - correo_electronico
    - password
    - rol (Cliente u Operador)

    Devuelve access y refresh tokens con duración distinta dependiendo del tipo de usuario.
    """
    rol = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        correo_electronico = attrs.get("correo_electronico")
        password = attrs.get("password")
        rol = attrs.get("rol")

        # Validar existencia del usuario
        try:
            usuario = Usuario.objects.get(correo_electronico=correo_electronico)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("Correo electrónico o contraseña incorrectos.")

        if usuario.tipo != rol:
            raise serializers.ValidationError("El rol indicado no coincide con el tipo de usuario.")

        user = authenticate(
            request=self.context.get('request'),
            correo_electronico=correo_electronico,
            password=password
        )

        if not user:
            raise serializers.ValidationError("Correo electrónico o contraseña incorrectos.")

        # Crear refresh y access tokens personalizados
        refresh = RefreshToken.for_user(user)

        # Token personalizado con duración distinta según tipo de usuario
        if user.tipo == 'Operador':
            access_token = AccessToken.for_user(user)
            access_token.set_exp(lifetime=timedelta(hours=10))
        elif user.tipo == 'Cliente':
            access_token = AccessToken.for_user(user)
            access_token.set_exp(lifetime=timedelta(minutes=10))
        else:
            access_token = AccessToken.for_user(user)  # default

        return {
            'refresh': str(refresh),
            'access': str(access_token),
            'usuario_id': user.id,
            'nombre': user.nombre,
            'tipo': user.tipo,
        }
    
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
class PerfilClienteAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UsuarioPerfilSerializer

    def get_object(self):
        # Esto asegura que solo el usuario autenticado vea/modifique su perfil
        return self.request.user


class CuentaCreateView(generics.CreateAPIView):
    """
    Crear una nueva cuenta bancaria (Solo operadores).

    Los operadores pueden crear cuentas para los clientes existentes.
    Se debe proporcionar el ID del cliente y los detalles de la cuenta (tipo, estado, etc.).
    """
    queryset = Cuenta.objects.all()
    serializer_class = CuentaSerializer
    permission_classes = [IsAuthenticated, EsOperador]
    
    @swagger_auto_schema(
        operation_summary="Crear cuenta bancaria",
        operation_description="Permite a un operador crear una cuenta para un cliente existente. Se debe enviar el correo del cliente y el tipo de cuenta."
    )
    def perform_create(self, serializer):
        serializer.save()
        
class TransaccionCreateView(generics.CreateAPIView):
    """
    Crear una transacción (depósito o retiro) como operador.

    El operador debe indicar:
    - tipo (Deposito o Retiro)
    - cantidad
    - cuenta origen (ID)

    El sistema valida si el saldo es suficiente (para retiros) y registra el operador que realizó la transacción.
    """
    queryset = Transaccion.objects.all()
    serializer_class = TransaccionSerializer
    permission_classes = [IsAuthenticated, EsOperador]
    
    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(id_operador=user)
    
class ActualizarContrasenaView(generics.UpdateAPIView):
    serializer_class = ActualizarContrasenaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
    
## Ver cuentas del cliente - Método GET
class MisCuentasView(generics.ListAPIView):
    """
    Ver las cuentas asociadas al usuario autenticado (solo clientes).

    Devuelve una lista de cuentas filtradas por el cliente autenticado.
    """
    serializer_class = CuentaDetalleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo cuentas del cliente autenticado
        return Cuenta.objects.filter(id_usuario=self.request.user)
    
"""
Transferencia de dinero entre cuentas

Ruta: /api/transacciones/transferir/
Método: POST
"""
class TransferenciaView(generics.CreateAPIView):
    """
    Realizar una transferencia entre cuentas (solo clientes).

    El cliente indica:
    - cuenta origen
    - cuenta destino
    - cantidad

    El sistema valida el saldo disponible y crea la transacción si es posible.
    """
    serializer_class = TransaccionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if user.tipo != 'Cliente':
            raise serializers.ValidationError("Solo los clientes pueden realizar transferencias.")
        serializer.save()
     
        
## Listar transacciones dependiendo del rol
class TransaccionListView(generics.ListAPIView):
    """
    Ver transacciones según el rol del usuario.

    - Clientes: ven sus transacciones (de sus cuentas).
    - Operadores: ven transacciones que ellos realizaron.
    """
    serializer_class = TransaccionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.tipo == 'Cliente':
            # Mostrar todas las transacciones donde el cliente sea dueño de la cuenta origen
            return Transaccion.objects.filter(id_cuenta__id_usuario=user).order_by('-fecha')

        elif user.tipo == 'Operador':
            # Mostrar solo transacciones donde el operador sea quien las realizó
            return Transaccion.objects.filter(id_operador=user).order_by('-fecha')

        # Si no es ni cliente ni operador, retornar un validation error
        raise serializers.ValidationError("Tipo de usuario no válido.")
    

# Vistas operador
# 1. Ver todos los clientes registrados
class ClienteListView(generics.ListAPIView):
    """
    Lista de todos los clientes registrados (solo operadores).

    Útil para buscar clientes y asignar cuentas o realizar transacciones.
    """
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated, EsOperador]

    def get_queryset(self):
        return Usuario.objects.filter(tipo='Cliente')


# 2. Ver logs de acciones
class LogListView(generics.ListAPIView):
    """
    Ver historial de acciones (logs) realizados por los usuarios (solo operadores).

    Se pueden aplicar filtros por:
    - ID del usuario
    - tipo de acción (e.g., transferencia, cancelación)
    """
    serializer_class = serializers.ModelSerializer
    permission_classes = [IsAuthenticated, EsOperador]

    class LogSerializer(serializers.ModelSerializer):
        class Meta:
            model = Log
            fields = '__all__'

    serializer_class = LogSerializer

    def get_queryset(self):
        queryset = Log.objects.all().order_by('-fecha')
        usuario_id = self.request.query_params.get("usuario_id")
        accion = self.request.query_params.get("accion")

        if usuario_id:
            queryset = queryset.filter(id_usuario__id_usuario=usuario_id)
        if accion:
            queryset = queryset.filter(accion__icontains=accion)

        return queryset


# 3. Cancelar una transacción (solo si está pendiente)
class CancelarTransaccionView(generics.UpdateAPIView):
    """
    Cancelar una transacción pendiente (solo operadores).

    Solo es posible cancelar si la transacción aún no ha sido completada.
    """
    serializer_class = TransaccionSerializer
    permission_classes = [IsAuthenticated, EsOperador]
    queryset = Transaccion.objects.all()

    def update(self, request, *args, **kwargs):
        transaccion = self.get_object()
        if transaccion.estado != 'Pendiente':
            raise serializers.ValidationError("Solo se pueden cancelar transacciones en estado Pendiente.")

        transaccion.estado = 'Cancelada'
        transaccion.save()

        Log.objects.create(
            id_usuario=request.user,
            accion="Cancelación de transacción",
            descripcion=f"Se canceló la transacción ID {transaccion.id_transaccion}"
        )

        return super().update(request, *args, **kwargs)


# 4. Buscar cliente por correo o nombre
class BuscarClienteView(generics.ListAPIView):
    """
    Buscar clientes por nombre o correo electrónico (solo operadores).
    
    Parámetro `q`: texto para buscar (nombre o correo).
    """
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated, EsOperador]

    def get_queryset(self):
        query = self.request.query_params.get("q", "")
        return Usuario.objects.filter(tipo='Cliente').filter(
            Q(nombre__icontains=query) | Q(correo_electronico__icontains=query)
        )


# 5. Buscar cuenta por número de cuenta
class BuscarCuentaView(generics.ListAPIView):
    """
    Buscar cuentas por número de cuenta (solo operadores).

    Parámetro `numero`: número parcial o completo de cuenta.
    """
    serializer_class = CuentaSerializer
    permission_classes = [IsAuthenticated, EsOperador]

    def get_queryset(self):
        numero = self.request.query_params.get("numero")
        return Cuenta.objects.filter(numero_cuenta__icontains=numero)


# 6. Reporte de transacciones por filtros
class ReporteTransaccionesView(generics.ListAPIView):
    """
    Reporte filtrado de transacciones (solo operadores).

    Parámetros opcionales:
    - tipo: tipo de transacción (Deposito, Retiro, Transferencia)
    - desde / hasta: rango de fechas (formato YYYY-MM-DD)
    - operador_id: ID del operador que ejecutó la transacción
    """
    serializer_class = TransaccionSerializer
    permission_classes = [IsAuthenticated, EsOperador]

    def get_queryset(self):
        queryset = Transaccion.objects.all().order_by('-fecha')
        tipo = self.request.query_params.get("tipo")
        desde = self.request.query_params.get("desde")  # formato YYYY-MM-DD
        hasta = self.request.query_params.get("hasta")
        operador_id = self.request.query_params.get("operador_id")

        if tipo:
            queryset = queryset.filter(tipo__iexact=tipo)
        if desde and hasta:
            queryset = queryset.filter(fecha__range=[desde, hasta])
        if operador_id:
            queryset = queryset.filter(id_operador__id_usuario=operador_id)

        return queryset

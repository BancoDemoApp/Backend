from rest_framework import serializers
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction as db_transaction
from .models import Usuario, Cuenta, Transaccion, Log
import random
from django.utils.timezone import now

class UsuarioSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Usuario.

    - Hashea la contraseña al crear el usuario.
    - Si el usuario es de tipo "Cliente", crea automáticamente
      una cuenta de ahorros activa asociada con número único.
    """

    class Meta:
        model = Usuario
        fields = [
            'id',
            'nombre',
            'correo_electronico',
            'telefono',
            'password',
            'tipo',
            'fecha_registro'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'fecha_registro': {'read_only': True}
        }

    # ---------------- CREACIÓN ---------------- #

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        usuario = Usuario.objects.create(**validated_data)

        if usuario.tipo == 'Cliente':
            self._crear_cuenta_ahorros(usuario)

        return usuario

    # ---------------- LÓGICA DE CUENTA ---------------- #

    def _crear_cuenta_ahorros(self, usuario):
        """
        Crea automáticamente una cuenta de ahorros activa
        para un usuario de tipo Cliente.
        """
        Cuenta.objects.create(
            numero_cuenta=self._generate_unique_numero_cuenta(),
            tipo='Ahorros',
            saldo=0.00,
            estado='Activa',
            id_usuario=usuario
        )

    def _generate_numero_cuenta(self):
        """
        Genera un número de cuenta con formato 999-9999999-99.
        """
        parte1 = str(random.randint(100, 999))
        parte2 = str(random.randint(1000000, 9999999))
        parte3 = str(random.randint(10, 99))
        return f"{parte1}-{parte2}-{parte3}"

    def _generate_unique_numero_cuenta(self):
        """
        Genera un número de cuenta único, con máximo 10 intentos.
        """
        for _ in range(10):
            numero = self._generate_numero_cuenta()
            if not Cuenta.objects.filter(numero_cuenta=numero).exists():
                return numero
        raise serializers.ValidationError("No se puede generar un número de cuenta único.")

    
class ActualizarContrasenaSerializer(serializers.Serializer):
    """
    Serializer para actualizar la contraseña de un usuario.
    Realiza las siguientes validaciones:
    - Verifica que la contraseña actual sea correcta.
    - Comprueba que la nueva contraseña coincida con la confirmación.
    - Evita que la nueva contraseña sea igual a la actual.
    """

    contrasena_actual = serializers.CharField(write_only=True)
    nueva_contrasena = serializers.CharField(write_only=True)
    confirmar_contrasena = serializers.CharField(write_only=True)

    # ---------------- VALIDACIONES ---------------- #

    def validate(self, attrs):
        user = self.context['request'].user
        contrasena_actual = attrs.get("contrasena_actual")
        nueva_contrasena = attrs.get("nueva_contrasena")
        confirmar_contrasena = attrs.get("confirmar_contrasena")

        self._validate_contrasena_actual(user, contrasena_actual)
        self._validate_coincidencia(nueva_contrasena, confirmar_contrasena)
        self._validate_no_repetida(contrasena_actual, nueva_contrasena)

        return attrs

    def _validate_contrasena_actual(self, user, contrasena_actual):
        """Verifica que la contraseña actual ingresada sea correcta."""
        if not check_password(contrasena_actual, user.password):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")

    def _validate_coincidencia(self, nueva, confirmar):
        """Verifica que la nueva contraseña y su confirmación coincidan."""
        if nueva != confirmar:
            raise serializers.ValidationError("Las nuevas contraseñas no coinciden.")

    def _validate_no_repetida(self, actual, nueva):
        """Evita que la nueva contraseña sea igual a la actual."""
        if actual == nueva:
            raise serializers.ValidationError("La nueva contraseña no puede ser igual a la actual.")

    # ---------------- ACTUALIZACIÓN ---------------- #

    def save(self, **kwargs):
        """
        Actualiza la contraseña del usuario autenticado.
        """
        user = self.context['request'].user
        nueva = self.validated_data["nueva_contrasena"]
        user.password = make_password(nueva)
        user.save()
        return user
    

class UsuarioPerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['nombre', 'correo_electronico', 'telefono', 'fecha_registro']
        read_only_fields = ['fecha_registro']

    def update(self, instance, validated_data):
        # Sólo se permite actualizar nombre, correo y teléfono
        instance.nombre = validated_data.get('nombre', instance.nombre)
        instance.correo_electronico = validated_data.get('correo_electronico', instance.correo_electronico)
        instance.telefono = validated_data.get('telefono', instance.telefono)
        instance.save()
        return instance
    
    
class CuentaSerializer(serializers.Serializer):
    """
    Serializer para la creación de cuentas bancarias por parte de un operador.
    
    Requiere el correo del cliente y el tipo de cuenta (Ahorros o Corriente).
    """
    correo_cliente = serializers.EmailField(write_only = True)
    tipo = serializers.ChoiceField(choices=['Ahorros', 'Corriente'])

    def generate_numero_cuenta(self):
        parte1 = str(random.randint(100, 999))
        parte2 = str(random.randint(1000000, 9999999))
        parte3 = str(random.randint(10, 99))
        return f"{parte1}-{parte2}-{parte3}"

    def generate_unique_numero_cuenta(self):
        for _ in range(10):
            numero = self.generate_numero_cuenta()
            if not Cuenta.objects.filter(numero_cuenta=numero).exists():
                return numero
        raise serializers.ValidationError("No se pudo generar un número de cuenta único.")

    @db_transaction.atomic
    def create(self, validated_data):
        correo_cliente = validated_data['correo_cliente']
        tipo = validated_data['tipo']
        operador = self.context['request'].user

        # Validar que quien hace la solicitud es un operador
        if operador.tipo != 'Operador':
            raise serializers.ValidationError("Solo operadores pueden crear cuentas.")

        # Buscar al cliente
        try:
            cliente = Usuario.objects.get(correo_electronico=correo_cliente, tipo='Cliente')
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("No se encontró un cliente con ese correo.")

        # Crear la cuenta
        cuenta = Cuenta.objects.create(
            numero_cuenta=self.generate_unique_numero_cuenta(),
            tipo=tipo,
            saldo=0.00,
            estado='Activa',
            id_usuario=cliente
        )

        # Crear log de auditoría
        Log.objects.create(
            id_usuario=operador,
            accion="Creación de cuenta",
            descripcion=f"Se creó una cuenta de tipo {tipo} para el cliente {cliente.correo_electronico} (ID {cliente.id})"
        )

        return cuenta
    

class UsuarioSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'correo_electronico']

class CuentaDetalleSerializer(serializers.ModelSerializer):
    id_usuario = UsuarioSimpleSerializer(read_only=True)

    class Meta:
        model = Cuenta
        fields = ['id_cuenta', 'numero_cuenta', 'tipo', 'saldo', 'estado', 'id_usuario']
    
   
class TransaccionSerializer(serializers.ModelSerializer):
    """
    Serializer para registrar depósitos, retiros y transferencias.

    - Operadores pueden hacer depósitos y retiros.
    - Clientes pueden hacer transferencias entre cuentas propias y otras.
    """

    correo_cliente = serializers.EmailField(write_only=True, required=False)  # Solo para operadores
    numero_cuenta_destino = serializers.CharField(write_only=True, required=False)  # Solo para transferencias
    id_cuenta_id = serializers.IntegerField(write_only=True)  # Recibe el ID desde el frontend

    class Meta:
        model = Transaccion
        fields = [
            'id_transaccion',
            'tipo',
            'cantidad',
            'fecha',
            'estado',
            'id_cuenta',             # Relación a objeto Cuenta (read-only)
            'id_cuenta_id',          # Campo de entrada real
            'correo_cliente',
            'numero_cuenta_destino',
            'id_operador',
            'id_cuenta_destino',
        ]
        read_only_fields = ['estado', 'fecha', 'id_operador', 'id_cuenta', 'id_cuenta_destino']

    # ---------------- VALIDACIONES ---------------- #

    def validate(self, attrs):
        user = self.context['request'].user
        tipo = attrs.get('tipo')
        cantidad = attrs.get('cantidad')
        cuenta_id = attrs.get('id_cuenta_id')

        cuenta_origen = self._get_cuenta_origen(cuenta_id)
        attrs['id_cuenta'] = cuenta_origen

        self._validate_cantidad(cantidad)
        self._validate_tipo_transaccion(user, tipo, attrs, cuenta_origen, cantidad)

        return attrs

    def _get_cuenta_origen(self, cuenta_id):
        try:
            return Cuenta.objects.get(pk=cuenta_id)
        except Cuenta.DoesNotExist:
            raise serializers.ValidationError("La cuenta de origen no existe.")

    def _validate_cantidad(self, cantidad):
        if cantidad is None or cantidad <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a cero.")

    def _validate_tipo_transaccion(self, user, tipo, attrs, cuenta_origen, cantidad):
        if tipo in ['Deposito', 'Retiro']:
            self._validate_operador(user, attrs, cuenta_origen)
        elif tipo == 'Transferencia':
            self._validate_transferencia(user, cuenta_origen, cantidad, attrs)
        else:
            raise serializers.ValidationError("Tipo de transacción no válido.")

    def _validate_operador(self, user, attrs, cuenta_origen):
        if user.tipo != 'Operador':
            raise serializers.ValidationError("Solo operadores pueden realizar depósitos o retiros.")
        correo = attrs.get('correo_cliente')
        if not correo:
            raise serializers.ValidationError("Debe especificar el correo del cliente.")
        if cuenta_origen.id_usuario.correo_electronico != correo:
            raise serializers.ValidationError("La cuenta no pertenece al cliente especificado.")

    def _validate_transferencia(self, user, cuenta_origen, cantidad, attrs):
        if user.tipo != 'Cliente':
            raise serializers.ValidationError("Solo clientes pueden realizar transferencias.")
        if cuenta_origen.id_usuario != user:
            raise serializers.ValidationError("La cuenta no le pertenece al usuario autenticado.")
        attrs['estado'] = 'Cancelada' if cantidad > cuenta_origen.saldo else 'Pendiente'

    # ---------------- CREACIÓN DE TRANSACCIÓN ---------------- #

    @db_transaction.atomic
    def create(self, validated_data):
        tipo = validated_data['tipo']
        cuenta_origen = validated_data['id_cuenta']
        cantidad = validated_data['cantidad']
        user = self.context['request'].user
        estado = validated_data.get('estado', 'Pendiente')

        transaccion_data = self._build_base_transaccion_data(tipo, cantidad, cuenta_origen, estado)

        if tipo == 'Transferencia':
            estado = self._procesar_transferencia(validated_data, cuenta_origen, cantidad, transaccion_data)
        elif tipo == 'Deposito':
            estado = self._procesar_deposito(cuenta_origen, cantidad, user, transaccion_data)
        elif tipo == 'Retiro':
            estado = self._procesar_retiro(cuenta_origen, cantidad, user, transaccion_data)

        transaccion_data['estado'] = estado
        transaccion = Transaccion.objects.create(**transaccion_data)

        self._crear_log(user, tipo, cantidad, cuenta_origen, estado)

        return transaccion

    # ---------------- MÉTODOS AUXILIARES CREACIÓN ---------------- #

    def _build_base_transaccion_data(self, tipo, cantidad, cuenta_origen, estado):
        return {
            'tipo': tipo,
            'cantidad': cantidad,
            'id_cuenta': cuenta_origen,
            'estado': estado,
        }

    def _procesar_transferencia(self, validated_data, cuenta_origen, cantidad, transaccion_data):
        num_destino = validated_data.get('numero_cuenta_destino')
        try:
            cuenta_destino = Cuenta.objects.get(numero_cuenta=num_destino)
        except Cuenta.DoesNotExist:
            return 'Cancelada'

        if cantidad <= cuenta_origen.saldo:
            cuenta_origen.saldo -= cantidad
            cuenta_destino.saldo += cantidad
            cuenta_origen.save()
            cuenta_destino.save()
            transaccion_data['id_cuenta_destino'] = cuenta_destino
            return 'Completada'

        return 'Cancelada'

    def _procesar_deposito(self, cuenta_origen, cantidad, user, transaccion_data):
        transaccion_data['id_operador'] = user
        cuenta_origen.saldo += cantidad
        cuenta_origen.save()
        return 'Completada'

    def _procesar_retiro(self, cuenta_origen, cantidad, user, transaccion_data):
        transaccion_data['id_operador'] = user
        if cuenta_origen.saldo >= cantidad:
            cuenta_origen.saldo -= cantidad
            cuenta_origen.save()
            return 'Completada'
        return 'Cancelada'

    def _crear_log(self, user, tipo, cantidad, cuenta_origen, estado):
        Log.objects.create(
            id_usuario=user,
            accion=tipo,
            descripcion=f"Transacción {tipo} de {cantidad} en cuenta {cuenta_origen.numero_cuenta} con estado {estado}."
        )
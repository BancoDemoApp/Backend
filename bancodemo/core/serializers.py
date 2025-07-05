from rest_framework import serializers
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction as db_transaction
from .models import Usuario, Cuenta, Transaccion, Log
import random

class UsuarioSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Usuario.
    
    Este serializer gestiona la creación de usuarios, y si el tipo es "Cliente",
    se crea automáticamente una cuenta de ahorros activa asociada.
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
            'password': { 'write_only': True },
            'fecha_registro': { 'read_only': True }
        }

    def generate_numero_cuenta(self):
        """
        Genera un número de cuenta en el formato 999-9999999-99
        """
        parte1 = str(random.randint(100, 999))
        parte2 = str(random.randint(1000000, 9999999))
        parte3 = str(random.randint(10, 99))
        return f"{parte1}-{parte2}-{parte3}"

    def generate_unique_numero_cuenta(self):
        """
        Intenta generar un número de cuenta único.
        """
        intentos = 0
        while True:
            numero = self.generate_numero_cuenta()
            if not Cuenta.objects.filter(numero_cuenta=numero).exists():
                return numero
            intentos += 1
            if intentos > 10:
                raise serializers.ValidationError("No se puede generar un número de cuenta único.")

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        usuario = Usuario.objects.create(**validated_data)

        # Si el usuario es de tipo 'Cliente', crear cuenta de ahorros automáticamente
        if usuario.tipo == 'Cliente':
            Cuenta.objects.create(
                numero_cuenta=self.generate_unique_numero_cuenta(),
                tipo='Ahorros',
                saldo=0.00,
                estado='Activa',
                id=usuario
            )

        return usuario
    
class ActualizarContrasenaSerializer(serializers.Serializer):
    contrasena_actual = serializers.CharField(write_only=True)
    nueva_contrasena = serializers.CharField(write_only=True)
    confirmar_contrasena = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        contrasena_actual = attrs.get('contrasena_actual')
        nueva_contrasena = attrs.get('nueva_contrasena')
        confirmar_contrasena = attrs.get('confirmar_contrasena')

        if not check_password(contrasena_actual, user.password):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")

        if nueva_contrasena != confirmar_contrasena:
            raise serializers.ValidationError("Las nuevas contraseñas no coinciden.")

        if contrasena_actual == nueva_contrasena:
            raise serializers.ValidationError("La nueva contraseña no puede ser igual a la actual.")

        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.password = make_password(self.validated_data['nueva_contrasena'])
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
    
class CuentaDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuenta
        fields = [
            'id_cuenta',
            'numero_cuenta',
            'tipo',
            'saldo',
            'estado',
        ]
    
    
class TransaccionSerializer(serializers.ModelSerializer):
    """
    Serializer para registrar depósitos, retiros y transferencias.

    - Operadores pueden hacer depósitos y retiros.
    - Clientes pueden hacer transferencias entre cuentas propias y otras.
    """
    correo_cliente = serializers.EmailField(write_only=True, required=False)  # Solo para operadores
    numero_cuenta_destino = serializers.CharField(write_only=True, required=False)  # Solo para transferencias

    class Meta:
        model = Transaccion
        fields = [
            'id_transaccion',
            'tipo',
            'cantidad',
            'fecha',
            'estado',
            'id_cuenta',
            'correo_cliente',
            'numero_cuenta_destino',
            'id_operador',
            'id_cuenta_destino',
        ]
        read_only_fields = ['estado', 'fecha', 'id_operador', 'id_cuenta_destino']

    def validate(self, attrs):
        user = self.context['request'].user
        tipo = attrs.get('tipo')
        cantidad = attrs.get('cantidad')
        cuenta_origen = attrs.get('id_cuenta')

        # Nueva validación: evitar montos negativos o cero
        if cantidad is None or cantidad <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a cero.")

        if tipo in ['Deposito', 'Retiro']:
            if user.tipo != 'Operador':
                raise serializers.ValidationError("Solo operadores pueden realizar depósitos o retiros.")
            correo = attrs.get('correo_cliente')
            if not correo:
                raise serializers.ValidationError("Debe especificar el correo del cliente.")
            if cuenta_origen.id_usuario.correo_electronico != correo:
                raise serializers.ValidationError("La cuenta no pertenece al cliente especificado.")

        elif tipo == 'Transferencia':
            if user.tipo != 'Cliente':
                raise serializers.ValidationError("Solo clientes pueden realizar transferencias.")
            if cuenta_origen.id_usuario != user:
                raise serializers.ValidationError("La cuenta no le pertenece al usuario autenticado.")
            if cantidad > cuenta_origen.saldo:
                attrs['estado'] = 'Cancelada'
            else:
                attrs['estado'] = 'Pendiente'

        else:
            raise serializers.ValidationError("Tipo de transacción no válido.")

        return attrs

    @db_transaction.atomic
    def create(self, validated_data):
        tipo = validated_data['tipo']
        cuenta_origen = validated_data['id_cuenta']
        cantidad = validated_data['cantidad']
        user = self.context['request'].user
        estado = validated_data.get('estado', 'Pendiente')

        transaccion_data = {
            'tipo': tipo,
            'cantidad': cantidad,
            'id_cuenta': cuenta_origen,
            'estado': estado,
        }

        if tipo == 'Transferencia':
            num_destino = validated_data.get('numero_cuenta_destino')
            try:
                cuenta_destino = Cuenta.objects.get(numero_cuenta=num_destino)
            except Cuenta.DoesNotExist:
                estado = 'Cancelada'
            else:
                if cantidad <= cuenta_origen.saldo:
                    cuenta_origen.saldo -= cantidad
                    cuenta_destino.saldo += cantidad
                    cuenta_origen.save()
                    cuenta_destino.save()
                    estado = 'Completada'
                else:
                    estado = 'Cancelada'

                transaccion_data['id_cuenta_destino'] = cuenta_destino

        elif tipo == 'Deposito':
            cuenta_origen.saldo += cantidad
            cuenta_origen.save()
            estado = 'Completada'
            transaccion_data['id_operador'] = user

        elif tipo == 'Retiro':
            if cuenta_origen.saldo >= cantidad:
                cuenta_origen.saldo -= cantidad
                cuenta_origen.save()
                estado = 'Completada'
            else:
                estado = 'Cancelada'
            transaccion_data['id_operador'] = user

        transaccion_data['estado'] = estado

        transaccion = Transaccion.objects.create(**transaccion_data)

        # Crear log automáticamente
        Log.objects.create(
            id_usuario=user,
            accion=f"{tipo}",
            descripcion=f"Transacción {tipo} de {cantidad} en cuenta {cuenta_origen.numero_cuenta} con estado {estado}."
        )

        return transaccion

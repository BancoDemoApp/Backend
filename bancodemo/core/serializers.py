from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Usuario, Cuenta
import random

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            'id_usuario',
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
        
    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return Usuario.objects.create(**validated_data)
    
    
class CuentaSerializer(serializers.ModelSerializer):
    class Meta:
        model=Cuenta
        fields = [
            'id_cuenta', 
            'numero_cuenta', 
            'tipo',
            'saldo',
            'estado',
            'id_usuario'
        ]
        read_only_fields = ['numero_cuenta', 'saldo']
        
    def validate_tipo(self, value):
        if value not in ['Ahorros', 'Corriente']:
            raise serializers.ValidationError("Tipo de cuenta debe ser 'Ahorros' o 'Corriente'.")
        return value
    
    def validate_estado(self, value):
        if value not in ['Activa', 'Inactiva']:
            raise serializers.ValidationError("Tipo de cuenta debe ser 'Activa' o 'Inactiva'.")
        return value
    
    def generate_numero_cuenta(self):
        """Genera un número con formato XXX-XXXXXXX-XX"""
        parte1 = str(random.randint(100, 999))
        parte2 = str(random.randint(1000000, 9999999))
        parte3 = str(random.randint(10, 99))
        return f"{parte1}-{parte2}-{parte3}"
    
    def generate_unique_numero_cuenta(self):
        intentos = 0
        while True:
            numero = self.generate_numero_cuenta()
            if not Cuenta.objects.filter(numero_cuenta=numero).exists():
                return numero
            intentos += 1
            if intentos > 10:
                raise serializers.ValidationError("No se puede generar un número de cuenta único.")
    
    def create(self, validated_data):
        validated_data['numero_cuenta'] = self.generate_unique_numero_cuenta()
        validated_data['saldo'] = 0.00
        return Cuenta.objects.create(**validated_data)
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Usuario

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
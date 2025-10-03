from rest_framework import serializers
from .models import Responsable

class ResponsableSerializer(serializers.ModelSerializer):
    Responsable_photo = serializers.SerializerMethodField()

    class Meta:
        model = Responsable
        fields = '__all__'

    def get_Responsable_photo(self, obj):
        if obj.Responsable_photo:
            return obj.Responsable_photo.url
        return ""

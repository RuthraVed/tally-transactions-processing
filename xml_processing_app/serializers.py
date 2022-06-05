from rest_framework import serializers
from .models import ProcessedTransaction
class ProcessedTransactionSerializer(serializers.ModelSerializer):
 
    class Meta:
        model = ProcessedTransaction
        fields = '__all__'
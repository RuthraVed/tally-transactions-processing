from django.contrib import admin
from .models import ProcessedTransaction

@admin.register(ProcessedTransaction)
class ProcessedTransactionAdmin(admin.ModelAdmin):
    list_display = ('process_id', 'input_xml', 'output_xlsx', 'started_at', 'finished_at')
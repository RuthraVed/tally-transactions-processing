from django.db import models
from datetime import datetime
from pathlib import Path

# A callable function for 'upload_to=' 
# to be used inside models.FileField
def path_and_rename(instance, filename):
    
    upload_to = ''
    if '.xml' in filename:
        upload_to = datetime.now().strftime('xml_files/%Y/%m/%d/')
    elif '.xlsx' in filename:
        upload_to = datetime.now().strftime('xlsx_files/%Y/%m/%d/')
    else:
        upload_to = datetime.now().strftime('other_files/%Y/%m/%d/')

    name = filename.split('.')[0]
    ext = filename.split('.')[-1]   # Ensures to pick from end so that it is ext always
    filename = name + '__' + datetime.now().strftime('%I-%p.') + ext

    return f'{upload_to}/{filename}'

class ProcessedTransaction(models.Model):
    process_id = models.BigAutoField(primary_key=True)
    input_xml = models.FileField(
        null=False,
        blank=False,
        db_column='Input .xml column',
        verbose_name='Tally Input.xml',
        upload_to=path_and_rename,

    )
    output_xlsx = models.FileField(
        null=True,
        blank=True,
        db_column='Output .xlsx column',
        verbose_name='Tally Response.xlsx ',
        # upload_to=datetime.now().strftime('xlsx_files/%Y/%m/%d/'),
        upload_to = path_and_rename,

    )
    started_at = models.DateTimeField(auto_now_add=True, editable=False)
    finished_at = models.DateTimeField(auto_now=True, editable=False)
 
    class Meta:
        verbose_name_plural = 'Processed Transactions'



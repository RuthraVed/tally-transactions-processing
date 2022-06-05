from rest_framework import viewsets, parsers
from .models import ProcessedTransaction
from .serializers import ProcessedTransactionSerializer
from rest_framework.response import Response
from rest_framework import status
from django.core.files.base import ContentFile
import xlsxwriter
from bs4 import BeautifulSoup
import io


class ProcessedTransactionViewset(viewsets.ModelViewSet): 
    queryset = ProcessedTransaction.objects.all().order_by('-process_id')[:3]
    serializer_class = ProcessedTransactionSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def create(self, request, *args, **kwargs):
        
        # Step 1: Create a new DB entry only with filed "input_xml"
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Step 2: Fetching the newly added entry by it's "process_id"
        current_process_obj = ProcessedTransaction.objects.get(process_id=serializer.data['process_id'])
        
        # Step 3: Processing the "input_xml" by calling the process_xml() on it.
        response_xlsx = process_xml(current_process_obj.input_xml)
        # and saving the return value in ContentFile obj
        contentFile = ContentFile(response_xlsx)

        # Step 4: Saving the Response.xlsx using class FileFiled's save()
        current_process_obj.output_xlsx.save('Response.xlsx', contentFile.open(mode='r'))

        # Step 5: Fetching the same DB obj, so that it can be serialized again.
        single_query = ProcessedTransaction.objects.get(process_id=serializer.data['process_id'])
        serializer = ProcessedTransactionSerializer(single_query)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


# Some custom classes to hold extracted data from the input_xml
class ParentTransaction:
    def __init__(self, date, voucher_no, debtor):
        self.date = date
        self.transaction_type = "Parent"
        self.voucher_no = voucher_no
        self.voucher_type = "Receipt"
        self.debtor = debtor.title()
        self.particulars = self.debtor
        self.amount = 0.0
        self.amount_verified = "No"
        self.ref_no = "NA"
        self.ref_type = "NA"
        self.ref_date = "NA"
        self.ref_amount = "NA"

    def set_amount(self, ref_amount):
        self.amount += ref_amount

    def verify_amount(self, input_file_amount):
        if self.amount == float(input_file_amount):
            self.amount_verified = "Yes"


class ChildTransaction(ParentTransaction):
    def __init__(self, parent, ref_no, ref_type, ref_date, ref_amount):
        ParentTransaction.__init__(self, parent.date, parent.voucher_no, parent.debtor)
        self.transaction_type = "Child"
        self.ref_no = ref_no
        self.ref_type = ref_type
        self.ref_date = ref_date
        self.ref_amount = ref_amount
        self.amount = "NA"
        self.amount_verified = "NA"


class OtherTransaction(ParentTransaction):
    def __init__(self, parent, amount, debtor):
        ParentTransaction.__init__(self, parent.date, parent.voucher_no, parent.debtor)
        self.transaction_type = "Other"
        self.debtor = debtor.title()
        self.particulars = self.debtor
        self.amount = amount
        self.amount_verified = "NA"

'''
    A method to take in the file path inside DB field "input_xml"
    and return back a File() obj of .xlsx file type
    based on given processing logic.

    :request: path/to/input_xml
    :return: Django File obj of .xlsx type
    '''        
def process_xml(xml_filepath):
    # Here we deal with FileField and so using it's class methods
    # Eg. FileField.name, FileField.path, FileField.url and so.

    contents = ''
    with open(xml_filepath.path, mode='r') as f_in:
        contents = f_in.read()

    soup = BeautifulSoup(contents, 'xml')

    # Create an in-memory output file for the new workbook.
    output = io.BytesIO()

    # Create a new workbook and add a worksheet.
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # Add a bold format to use to highlight cells.
    bold = workbook.add_format({'bold': True})

    # Some data to write to the worksheet headers.
    WORKSHEET_HEADERS = (
        'Date',
        'Transaction Type',
        'Vch No.',
        'Ref No',
        'Ref Type',
        'Ref Date',
        'Debtor',
        'Ref Amount',
        'Amount',
        'Particulars',
        'Vch Type',
        'Amount Verified',
    )
    
    # # Start from the first cell. Rows and columns are zero indexed.
    # Iterate over the data and write it out row by row.
    row, col = 0, 0
    for header in WORKSHEET_HEADERS:
        worksheet.write(row, col, header, bold)
        col += 1


    # Start again from the first cell, below the headers.
    row = 1
    # Finding all VOUCHER tags, with attribute VCHTYPE as Receipt
    parents_list = soup.findAll("VOUCHER", {"VCHTYPE" : "Receipt"})
    for item in parents_list:
        date = item.find('DATE').text
        voucher_no = item.find('VOUCHERNUMBER').text
        debtor = item.find('PARTYLEDGERNAME').text
        parent_obj = ParentTransaction(date=date, voucher_no=voucher_no, debtor=debtor)

        child_objs_list = []
        other_objs_list = []
        input_file_amount = ""
        children_list  = item.findAll('ALLLEDGERENTRIES.LIST')
        if children_list:
            for child_item in children_list:
                ledgerName = child_item.find('LEDGERNAME')
                if ledgerName is not None and "bank" not in ledgerName.text.lower():
                    # Use of ternary operator
                    input_file_amount = child_item.find('AMOUNT').text if child_item.find('AMOUNT') else ""

                grand_children_list = child_item.findAll('BILLALLOCATIONS.LIST')
                if grand_children_list:
                    for grandchild_item in grand_children_list:
                        billType = grandchild_item.find('BILLTYPE')
                        if billType is not None and "ref" in billType.text.lower():
                            ref_no = grandchild_item.find('NAME').text
                            ref_type = grandchild_item.find('BILLTYPE').text
                            ref_date = grandchild_item.find('DATE').text if grandchild_item.find('DATE') else ""
                            ref_amount = grandchild_item.find('AMOUNT').text
                            parent_obj.set_amount(ref_amount=float(ref_amount))
                            child_objs_list.append(ChildTransaction(parent=parent_obj, ref_no=ref_no, ref_type=ref_type, ref_date=ref_date, ref_amount=ref_amount))
                        
                otherTypeName = child_item.find('LEDGERNAME')
                if otherTypeName is not None and "bank" in otherTypeName.text.lower():
                    debtor = otherTypeName.text
                    amount = child_item.find('AMOUNT').text
                    other_objs_list.append(OtherTransaction(parent=parent_obj, amount=amount, debtor=debtor))
        
        parent_obj.verify_amount(input_file_amount=input_file_amount)

        # Converting & saving all objects to object_dict. 
        obj_dicts_list = []
        obj_dicts_list.append(parent_obj.__dict__)
        for child_obj in child_objs_list:
            obj_dicts_list.append(child_obj.__dict__)
        for other_obj in other_objs_list:
            obj_dicts_list.append(other_obj.__dict__)


        # Iterate over the data and write it out row by row.
        for i in range(0, len(obj_dicts_list)):
            obj_dict = obj_dicts_list[i]
            worksheet.write(row, 0, obj_dict['date'])
            worksheet.write(row, 1, obj_dict['transaction_type'])
            worksheet.write(row, 2, obj_dict['voucher_no'])
            worksheet.write(row, 3, obj_dict['ref_no'])
            worksheet.write(row, 4, obj_dict['ref_type'])
            worksheet.write(row, 5, obj_dict['ref_date'])
            worksheet.write(row, 6, obj_dict['debtor'])
            worksheet.write(row, 7, obj_dict['ref_amount'])
            worksheet.write(row, 8, obj_dict['amount'])
            worksheet.write(row, 9, obj_dict['particulars'])
            worksheet.write(row, 10, obj_dict['voucher_type'])
            worksheet.write(row, 11, obj_dict['amount_verified'])
            
            row += 1
    
    workbook.close()
    xlsx_data = output.getvalue()
    # xlsx_data contains the Excel file
    return xlsx_data
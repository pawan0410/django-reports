from django.shortcuts import render
from mssql.appointments import appointments

# Create your views here.


def index(request):
    return render(request, 'emr/utilization_report.html')
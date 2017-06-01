from django.shortcuts import render
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from emr.models import ResourceGroup
from emr.models import StatusGroup
from emr.models import ResourceUtilizationSlots
from emr.models import AppointmentTypeGroup
from emr.models import AppointmentType
from emr.models import Resource
from django.http import HttpResponse, JsonResponse

# Create your views here.


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ('id', 'name', 'original_id')


class ResourceGroupSerializer(serializers.ModelSerializer):
    resource_id = ResourceSerializer(many=True)

    class Meta:
        model = ResourceGroup
        fields = ('id', 'name', 'resource_id')


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusGroup
        fields = ('id','name', 'status_id')


class ResourceUtilizationSlotsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceUtilizationSlots
        fields = ('resource_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday')


class AppointmentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentType
        fields = ('id', 'name', 'original_id')


class AppointmentTypeGroupSerializer(serializers.ModelSerializer):
    appointment_type_id = AppointmentTypeSerializer(many=True)

    class Meta:
        model = AppointmentTypeGroup
        fields = ('name', 'appointment_type_id')


def utilisation_report(request):
    return render(request, 'utilization_report.html')


@api_view(['GET'])
def get_resource(request):
    resource_groups = ResourceGroup.objects.all()
    serializer = ResourceGroupSerializer(resource_groups, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_status(request):
    status_groups = StatusGroup.objects.all()
    serializer = StatusSerializer(status_groups, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_resource_utilisation_slots(request):
    resource_utilisation_slots_groups = ResourceUtilizationSlots.objects.all()
    serializer = ResourceUtilizationSlotsSerializer(resource_utilisation_slots_groups, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_appointment_type_group(request):
    get_appointment_type_groups = AppointmentTypeGroup.objects.all()
    serializer = AppointmentTypeGroupSerializer(get_appointment_type_groups,many=True)
    return Response(serializer.data)

# @api_view(['GET'])
# def get_reports(request):
#     appointments_s = ResourceGroup.objects.all()
#     serializer = ResourceGroupSerializer(resource_groups, many=True)
#     return Response(serializer.data)








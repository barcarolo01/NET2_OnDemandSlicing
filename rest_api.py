#!/usr/bin/env python3

from ryu.app.wsgi import ControllerBase, route, Response
import json

# Slices: name and status [Initial configuration, True = Active]
Slices = {
    "Guest": False,
    "Office": False,
    "IoT": False,
    "Assistance": False,
    "Telesurgery": False,
    "IDS": False,
    "Laboratory": False
}

IPs={}

INSTANCE_NAME = 'slicing_controller'

# ============================== REST API ============================== #
class RestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(RestController, self).__init__(req, link, data, **config)
        self.controller_app = data[INSTANCE_NAME]

    @route('slice', '/slice/add_Guest', methods=['POST'])
    def add_Guest(self, req, **kwargs):
        self.controller_app.add_Guest_slice()
        return Response(status=200, content_type='text/plain', body='Guest slice added.')

    @route('slice', '/slice/remove_Guest', methods=['POST'])
    def remove_Guest(self, req, **kwargs):
        self.controller_app.remove_Guest_slice()
        return Response(status=200, content_type='text/plain', body='Guest slice removed.')
    
    @route('slice', '/slice/add_Office', methods=['POST'])
    def add_Office(self, req, **kwargs):
        self.controller_app.add_Office_slice()
        return Response(status=200, content_type='text/plain', body='Office slice added.')

    @route('slice', '/slice/remove_Office', methods=['POST'])
    def remove_Office(self, req, **kwargs):
        self.controller_app.remove_Office_slice()
        return Response(status=200, content_type='text/plain', body='Office slice removed.')

    @route('slice', '/slice/add_IoT', methods=['POST'])
    def add_iot(self, req, **kwargs):
        self.controller_app.add_IoT_slice()
        return Response(status=200, content_type='text/plain', body='IoT slice added')

    @route('slice', '/slice/remove_IoT', methods=['POST'])
    def remove_iot(self, req, **kwargs):
        self.controller_app.remove_IoT_slice()
        return Response(status=200, content_type='text/plain', body='IoT slice removed.')
    
    @route('slice', '/slice/add_Assistance', methods=['POST'])
    def add_Assistance(self, req, **kwargs):
        # Extracting body of HTTP POST message and passing it to "add_Assistance_slice" method
        body_bytes = req.body  
        body = body_bytes.decode('utf-8')
        self.controller_app.add_Assistance_slice(body)
        return Response(status=200, content_type='text/plain', body='Assistance slice added.')

    @route('slice', '/slice/remove_Assistance', methods=['POST'])
    def remove_Assistance(self, req, **kwargs):
        self.controller_app.remove_Assistance_slice()
        return Response(status=200, content_type='text/plain', body='Assistance slice removed.')
    
    @route('slice', '/slice/add_IDS', methods=['POST'])
    def add_IDS(self, req, **kwargs):
        self.controller_app.add_IDS_slice()
        return Response(status=200, content_type='text/plain', body='IDS slice added.')

    @route('slice', '/slice/remove_IDS', methods=['POST'])
    def remove_IDS(self, req, **kwargs):
        self.controller_app.remove_IDS_slice()
        return Response(status=200, content_type='text/plain', body='IDS slice removed.')
    
    @route('slice', '/slice/add_Laboratory', methods=['POST'])
    def add_Laboratory(self, req, **kwargs):
        self.controller_app.add_Laboratory_slice()
        return Response(status=200, content_type='text/plain', body='Laboratory slice added.')

    @route('slice', '/slice/remove_Laboratory', methods=['POST'])
    def remove_Laboratory(self, req, **kwargs):
        self.controller_app.remove_Laboratory_slice()
        return Response(status=200, content_type='text/plain', body='Laboratory slice removed.')
    
    @route('slice', '/slice/add_Telesurgery', methods=['POST'])
    def add_Telesurgery(self, req, **kwargs):
        self.controller_app.add_Telesurgery_slice()
        return Response(status=200, content_type='text/plain', body='Telesurgery slice added.')
    
    @route('slice', '/slice/remove_Telesurgery', methods=['POST'])
    def remove_Telesurgery(self, req, **kwargs):
        self.controller_app.remove_Telesurgery_slice()
        return Response(status=200, content_type='text/plain', body='Telesurgery slice removed.')
    
    @route('slice', '/slice/get_slices', methods=['GET'])
    def get_slices(self, req, **kwargs):
        body = json.dumps(Slices)
        return Response(content_type='application/json', body=body, status=200)
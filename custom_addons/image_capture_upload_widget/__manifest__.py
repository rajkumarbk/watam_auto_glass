
{
    'name': 'Image Capture Widget',
    'version': '18.0.1.0.0',
    'category': 'Extra Tools',
    'summary': """This module allows to capture the users image from the
    webcam.""",
    'description': """This module is used to add Image Capture Widget for Image 
    Field. We can capture the image from the webcam and upload into the binary
    field.""",
    'author': 'Dishan Shrestha',
    'depends': [],
    'data': ['security/ir.model.access.csv'],
    'assets': {
        'web.assets_backend': [
            '/image_capture_upload_widget/static/src/scss/image_capture.scss',
            '/image_capture_upload_widget/static/src/js/image_capture.js',
            '/image_capture_upload_widget/static/src/xml/image_capture_templates.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

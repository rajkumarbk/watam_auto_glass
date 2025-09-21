from odoo import models


class ImageCapture(models.TransientModel):
    """ A model for capturing images """
    _name = 'image.capture'
    _description = 'Image Capture'

    def action_save_image(self,  url):
        """
        Saving the images to corresponding models
        :param url: Image details.
        """
        image = url.split(',')
        return image[1]

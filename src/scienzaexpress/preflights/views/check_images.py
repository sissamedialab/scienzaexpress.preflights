# -*- coding: utf-8 -*-

# from scienzaexpress.preflights import _
from Products.Five.browser import BrowserView
from zope.interface import implementer
from zope.interface import Interface

# from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

class ICheckImages(Interface):
    """ Marker Interface for ICheckImages"""


@implementer(ICheckImages)
class CheckImages(BrowserView):
    # If you want to define a template here, please remove the template from
    # the configure.zcml registration of this view.
    # template = ViewPageTemplateFile('check_images.pt')

    def __call__(self):
        # Implement your own actions:
        return self.index()

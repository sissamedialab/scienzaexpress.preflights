# -*- coding: utf-8 -*-
from scienzaexpress.preflights.testing import SCIENZAEXPRESS_PREFLIGHTS_FUNCTIONAL_TESTING
from scienzaexpress.preflights.testing import SCIENZAEXPRESS_PREFLIGHTS_INTEGRATION_TESTING
from scienzaexpress.preflights.views.check_images import ICheckImages
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from zope.component import getMultiAdapter
from zope.interface.interfaces import ComponentLookupError

import unittest


class ViewsIntegrationTest(unittest.TestCase):

    layer = SCIENZAEXPRESS_PREFLIGHTS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        api.content.create(self.portal, 'Folder', 'other-folder')
        api.content.create(self.portal, 'Document', 'front-page')

    def test_check_images_is_registered(self):
        view = getMultiAdapter(
            (self.portal['other-folder'], self.portal.REQUEST),
            name='check-images'
        )
        self.assertTrue(ICheckImages.providedBy(view))

    def test_check_images_not_matching_interface(self):
        view_found = True
        try:
            view = getMultiAdapter(
                (self.portal['front-page'], self.portal.REQUEST),
                name='check-images'
            )
        except ComponentLookupError:
            view_found = False
        else:
            view_found = ICheckImages.providedBy(view)
        self.assertFalse(view_found)


class ViewsFunctionalTest(unittest.TestCase):

    layer = SCIENZAEXPRESS_PREFLIGHTS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

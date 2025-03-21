from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from scienzaexpress.preflights.testing import (
    SCIENZAEXPRESS_PREFLIGHTS_FUNCTIONAL_TESTING,
)
from scienzaexpress.preflights.testing import (
    SCIENZAEXPRESS_PREFLIGHTS_INTEGRATION_TESTING,
)
from scienzaexpress.preflights.views.onix_generator import IOnixGenerator
from zope.component import getMultiAdapter
from zope.interface.interfaces import ComponentLookupError

import unittest


class ViewsIntegrationTest(unittest.TestCase):
    layer = SCIENZAEXPRESS_PREFLIGHTS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        api.content.create(self.portal, "Folder", "other-folder")
        api.content.create(self.portal, "Document", "front-page")

    def test_onix_generator_is_registered(self):
        view = getMultiAdapter(
            (self.portal["other-folder"], self.portal.REQUEST), name="onix-generator"
        )
        self.assertTrue(IOnixGenerator.providedBy(view))

    def test_onix_generator_not_matching_interface(self):
        view_found = True
        try:
            view = getMultiAdapter(
                (self.portal["front-page"], self.portal.REQUEST), name="onix-generator"
            )
        except ComponentLookupError:
            view_found = False
        else:
            view_found = IOnixGenerator.providedBy(view)
        self.assertFalse(view_found)


class ViewsFunctionalTest(unittest.TestCase):
    layer = SCIENZAEXPRESS_PREFLIGHTS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

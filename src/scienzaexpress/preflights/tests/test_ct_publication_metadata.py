from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from scienzaexpress.preflights.testing import (  # noqa
    SCIENZAEXPRESS_PREFLIGHTS_INTEGRATION_TESTING,
)
from zope.component import createObject
from zope.component import queryUtility

import unittest


try:
    from plone.dexterity.schema import portalTypeToSchemaName
except ImportError:
    # Plone < 5
    from plone.dexterity.utils import portalTypeToSchemaName


class PublicationMetadataIntegrationTest(unittest.TestCase):
    layer = SCIENZAEXPRESS_PREFLIGHTS_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.parent = self.portal

    def test_ct_metadata_schema(self):
        fti = queryUtility(IDexterityFTI, name="Metadata")
        schema = fti.lookupSchema()
        schema_name = portalTypeToSchemaName("Metadata")
        self.assertIn(schema_name.lstrip("plone_0_"), schema.getName())

    def test_ct_metadata_fti(self):
        fti = queryUtility(IDexterityFTI, name="Metadata")
        self.assertTrue(fti)

    def test_ct_metadata_factory(self):
        fti = queryUtility(IDexterityFTI, name="Metadata")
        factory = fti.factory
        createObject(factory)

    def test_ct_metadata_adding(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        obj = api.content.create(
            container=self.portal,
            type="Metadata",
            id="metadata",
        )

        parent = obj.__parent__
        self.assertIn("metadata", parent.objectIds())

        # check that deleting the object works too
        api.content.delete(obj=obj)
        self.assertNotIn("metadata", parent.objectIds())

    def test_ct_metadata_globally_addable(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        fti = queryUtility(IDexterityFTI, name="Metadata")
        self.assertTrue(fti.global_allow, f"{fti.id} is not globally addable!")

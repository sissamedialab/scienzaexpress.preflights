from plone.dexterity.content import Item
from plone.supermodel import model
from zope.interface import implementer


class IPublicationMetadata(model.Schema):
    """Marker interface for PublicationMetadata."""

    model.load("publication_metadata.xml")


@implementer(IPublicationMetadata)
class PublicationMetadata(Item):
    """Metadata for RISE types."""

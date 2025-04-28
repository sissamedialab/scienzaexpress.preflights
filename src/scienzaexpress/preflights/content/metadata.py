from plone.dexterity.content import Item
from plone.supermodel import model
from zope.interface import implementer


class IMetadata(model.Schema):
    """Marker interface for Metadata."""

    model.load("metadata.xml")


@implementer(IMetadata)
class Metadata(Item):
    """Metadata for RISE types."""

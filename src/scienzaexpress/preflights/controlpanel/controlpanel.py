from plone import schema
from zope.interface import Interface


class ISEMetaSettings(Interface):
    """
    List of typographies.

    See also profiles/defaults/registry/main.xml.
    """

    typographies = schema.List(
        title="Tipografie",
        description="Tipografie disponibili",
        required=False,
        value_type=schema.TextLine(),
        missing_value=[],
        default=[],
    )

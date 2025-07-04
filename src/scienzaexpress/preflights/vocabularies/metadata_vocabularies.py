from plone import api
from zope.interface import implementer
from zope.interface import provider
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary


@provider(IVocabularyFactory)
def typographies_vocabulary(context):
    """Get a vocabulary from the values stored in the registry."""
    items = api.portal.get_registry_record("se_meta.typographies")
    return SimpleVocabulary.fromItems(
        [[item, item] for item in items],
    )


@implementer(IContextSourceBinder)
class Binder:
    """Bind the typographies vocabulary with a context."""

    # see e.g. https://4.docs.plone.org/external/plone.app.dexterity/docs/reference/dexterity-xml.html#vocabularies

    def __call__(self, context):
        return typographies_vocabulary(context)


dummy_binder = Binder()

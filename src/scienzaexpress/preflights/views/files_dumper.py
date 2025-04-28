# from scienzaexpress.preflights import _
from pathlib import Path
from plone import api
from Products.Five.browser import BrowserView
from scienzaexpress.preflights.views.validate_pdf_metadata import (
    missing_metadata_message,
)
from scienzaexpress.preflights.views.validate_pdf_metadata import ValidatePdfMetadata
from zope.interface import implementer
from zope.interface import Interface

import shutil


class IFilesDumper(Interface):
    """Marker Interface for IFilesDumper"""


@implementer(IFilesDumper)
class FilesDumper(BrowserView):
    """Dump files of the current folder into app-friendly directory."""

    def __call__(self):
        pmo = ValidatePdfMetadata.find_metadata_object(self.context)
        if not pmo:
            api.portal.show_message(
                message=missing_metadata_message,
                request=self.request,
                type="error",
            )
            return self.index()

        # We assume that the pmo is inside a folder named "XML",
        # and this XML folder is inside the Type-specific object (Libro, Albo, etc.)
        ctype = pmo.aq_parent.aq_parent.portal_type
        ctype = ctype.replace(" ", "-").lower()  # just in case...

        # TODO: move this variable to a registry setting for this add-on
        root = Path.home() / "x"

        editorial_object_name = pmo.title.replace(" ", "-").lower()
        appfriendly_folder = root / ctype / editorial_object_name
        if appfriendly_folder.exists():
            # This process is destructive on the filesystem!
            shutil.rmtree(appfriendly_folder)
        appfriendly_folder.mkdir(parents=True, exist_ok=True)

        files_here = self.context.listFolderContents(
            contentFilter={"Type": "File"},
        )
        for file_obj in files_here:
            with open(appfriendly_folder / file_obj.file.filename, "wb") as file_fs:
                file_fs.write(file_obj.file.data)

        self.result = f"{len(files_here)} file scritti in {appfriendly_folder}"
        return self.index()

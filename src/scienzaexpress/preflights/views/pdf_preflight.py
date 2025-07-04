# from scienzaexpress.preflights import _
# from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from pathlib import Path
from plone.dexterity.interfaces import IDexterityItem
from Products.Five.browser import BrowserView
from zope.interface import implementer
from zope.interface import Interface

import dataclasses
import subprocess
import tempfile


class IPdfPreflight(Interface):
    """Marker Interface for IPdfPreflight"""


@dataclasses.dataclass(frozen=True)
class PdfImageInfo:
    """Represent an image as returned from pdfimages -list."""

    # $ pdfimages -list x.pdf
    # page   num  type   width height color comp bpc  enc interp  object ID x-ppi y-ppi size ratio
    # --------------------------------------------------------------------------------------------
    #    1     0 image     420   520  rgb     3   8  image  no         7  0   432   432  100K  16%
    # ...
    page: int
    num: int
    objecttype: str
    width: int
    height: int
    color: str
    comp: int
    bpc: int
    enc: str
    interp: str
    pdfobject: int
    pdfobjectid: int
    x_ppi: int
    y_ppi: int
    size: str
    ratio: str
    # name: str = dataclasses.field(init=False)

    def __str__(self):
        return f"{self.color} {self.objecttype} {self.width}x{self.height} ({self.x_ppi}x{self.y_ppi} ppi) at pg. {self.page}"


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """The result of a check."""

    file_obj: IDexterityItem
    image_name: str
    good: bool = False
    details: PdfImageInfo = None


@implementer(IPdfPreflight)
class PdfPreflight(BrowserView):
    # If you want to define a template here, please remove the template from
    # the configure.zcml registration of this view.
    # template = ViewPageTemplateFile('pdf_preflight.pt')

    def __call__(self):
        self.pdf_images_results = self.check_pdf_images()
        self.results = self.pdf_images_results
        return self.index()

    def check_pdf_images(self) -> list[list[CheckResult]]:
        """Verify that all images of all PDF files in this folder meet some requirements."""
        # see rise#24
        results = []
        pdf_files = self._get_all_pdf_objects()
        for file_obj in pdf_files:
            temp_path = self._temp_copy(file_obj)
            file_results = self._process_filepath(file_obj, temp_path)
            if file_results:
                results.append(file_results)
            temp_path.unlink()
        return results

    def _process_filepath(
        self,
        file_obj: IDexterityItem,
        temp_path: Path,
    ) -> list[CheckResult]:
        """Process one file."""
        proc = subprocess.run(
            ["pdfimages", "-list", temp_path],
            capture_output=True,
            text=True,
            check=False,
        )
        return self._parse_output(file_obj, proc)

    def _parse_output(self, file_obj, proc) -> list[CheckResult]:
        """Parse the output of pdfimages command for a certain file."""
        ppi_lowthreshold = 300

        stdout = proc.stdout.strip()
        # TODO: do something with the stderr?

        results = []
        lines = stdout.strip().split("\n")
        lines = lines[2:]
        # Process the remaining lines to split each into 16 fields
        for line in lines:
            parts = line.split()
            # TODO: if len(parts) != 16?
            pdfimageinfo = PdfImageInfo(
                page=int(parts[0]),
                num=int(parts[1]),
                objecttype=parts[2],
                width=int(parts[3]),
                height=int(parts[4]),
                color=parts[5],
                comp=parts[6],
                bpc=parts[7],
                enc=parts[8],
                interp=parts[9],
                pdfobject=parts[10],
                pdfobjectid=parts[11],
                x_ppi=int(parts[12]),
                y_ppi=int(parts[13]),
                size=parts[14],
                ratio=parts[15],
            )

            # 🌟 The (only) interesting logic is here!
            good = True
            if pdfimageinfo.x_ppi < ppi_lowthreshold:
                good = False
            if pdfimageinfo.y_ppi < ppi_lowthreshold:
                good = False

            results.append(
                CheckResult(
                    file_obj=file_obj,
                    image_name=str(pdfimageinfo),
                    good=good,
                    details=pdfimageinfo,
                ),
            )

        return results

    def _get_all_pdf_objects(self) -> list[IDexterityItem]:
        """Collect all Files that have .pdf extension."""
        file_objs = []
        pdf_types = ("application/pdf",)
        # Warning: do no use contentFilter={"Type": "File"}
        # because "Type" depends on the content-type _label_!!!
        for obj in self.context.listFolderContents(
            contentFilter={
                "portal_type": "File",
                "mime_type": "application/pdf",
            },
        ):
            if obj.file.contentType in pdf_types:
                file_objs.append(obj)
        return file_objs

    def _temp_copy(self, file_obj) -> Path:
        """Do a temporary copy of the file obj."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_obj.file.data)
            tmp_file.flush()
            temp_path = tmp_file.name
        return Path(temp_path)

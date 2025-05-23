from Products.Five.browser import BrowserView
from zope.interface import implementer
from zope.interface import Interface

import os
import subprocess
import tempfile


# from scienzaexpress.preflights import _  # Uncomment if using i18n


class ICheckImages(Interface):
    """Marker Interface for ICheckImages"""


@implementer(ICheckImages)
class CheckImages(BrowserView):
    # Code suggested by ChatGPT: 👍, but see "AI-ERROR"

    # We assume that check_images.pt is registered as the view template,
    # e.g. via zcml, so we use self.index() to render it.
    # If you wish to set the template here, uncomment the following line:
    # index = ViewPageTemplateFile('check_images.pt')

    def __call__(self):
        # import ipdb; ipdb.set_trace()
        self.results = []
        # Assume context is a folder; iterate over immediate child objects
        # for obj in self.context.objectValues("Image"):  AI-ERROR
        for obj in self.context.listFolderContents(contentFilter={"portal_type": "Image"}):
            # Ensure the object has an image field named 'image'
            if not hasattr(obj, "image"):
                continue

            image_field = obj.image
            if image_field is None:
                continue

            # Get the image data as bytes
            try:
                data = image_field.data
            except AttributeError:
                # If not available, skip the object.
                continue

            # Write image data to a temporary file so that ImageMagick can read it.
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                tmp_file.write(data)
                tmp_file.flush()
                temp_path = tmp_file.name

            # Call ImageMagick's 'identify' command on the temporary file.
            try:
                proc = subprocess.run(["identify", temp_path], capture_output=True, text=True, check=False)
                # Use stdout if available, else stderr.
                output = proc.stdout.strip() or proc.stderr.strip()
            except Exception as e:
                output = str(e)
            finally:
                # Clean up the temporary file.
                os.unlink(temp_path)

            # Append a result dict containing the image id and the identify output.
            self.results.append(
                {
                    "id": obj.getId(),
                    "identify_output": output,
                }
            )

        # Render the template (check_images.pt) which can use self.results.
        return self.index()

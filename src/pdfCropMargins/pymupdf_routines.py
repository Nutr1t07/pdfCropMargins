# -*- coding: utf-8 -*-
"""

Code that calls pyMuPDF.

=========================================================================

Some of this code is heavily modified from the GPL example/demo code found here:
https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_PDF_Viewer.py

Copyright (C) 2020 Allen Barker (Allen.L.Barker@gmail.com)
Source code site: https://github.com/abarker/pdfCropMargins

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

from __future__ import print_function, absolute_import
import sys
import warnings
from . import external_program_calls as ex

has_mupdf = True

try: # Extra dependencies for the GUI version.  Make sure they are installed.
    with warnings.catch_warnings():
        #warnings.filterwarnings("ignore",category=DeprecationWarning)
        import fitz
    if not [int(i) for i in fitz.VersionBind.split(".")] >= [1, 14, 5]:
        has_mupdf = False
        DocumentPages = None
except ImportError:
    has_mupdf = False
    DocumentPages = None

if has_mupdf:

    class DocumentPages:
        """Holds `pyMuPDF` document and rendered pages of the document for the GUI
        display.  Note that page numbering convention is from zero."""
        def __init__(self):
            self.clear_cache()

        def clear_cache(self):
            """Clear the cache of rendered document pages."""
            self.num_pages = 0
            self.page_display_list_cache = []
            self.page_crop_image_list_cache = []

        def open_document(self, doc_fname):
            """Open the document with fitz (PyMuPDF) and return the number of pages."""
            try:
                self.document = fitz.open(doc_fname)
            except RuntimeError:
                print("\nError in pdfCropMargins: The PyMuPDF program could not read"
                      " the document\n   '{}'\nin order to display it in the GUI.   If you have"
                      " Ghostscript installed\nconsider running pdfCropMargins with the"
                      " '--gsFix' option to attempt to repair it."
                      .format(doc_fname), file=sys.stderr)
                ex.cleanup_and_exit(1)
            self.num_pages = len(self.document)
            self.page_display_list_cache = [None] * self.num_pages
            self.page_crop_image_list_cache = [None] * self.num_pages
            return self.num_pages

        def close_document(self):
            """Close the document and clear its pages."""
            self.document.close()
            self.clear_cache()

        def get_page_ppm_for_crop(self, page_num):
            """Return an unscaled and unclipped `.ppm` file suitable for cropping the page.
            Not indended for displaying in the GUI."""
            # See: https://pymupdf.readthedocs.io/en/latest/colorspace.html#colorspace
            # Use grayscale for lower memory requirement; good enough for cropping.
            colorspace = fitz.csGRAY # or fitz.csRGB, or see above.

            page_crop_image_list = self.page_crop_image_list_cache[page_num]
            if not page_crop_image_list:  # Create if not yet there.
                self.page_crop_image_list_cache[page_num] = self.document[page_num].getDisplayList()
                page_crop_image_list = self.page_crop_image_list_cache[page_num]

            # Note, Matrix(2,2) gives more resolution.
            # https://github.com/pymupdf/PyMuPDF/issues/322 # Also info on opening in Pillow.
            # TODO: Above page also lists faster way than getting ppm first.
            #       Use in above: fitz.csGRAY and mode R (did he mean mode L?)
            # https://pillow.readthedocs.io/en/stable/reference/Image.html
            # https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes
            # https://pymupdf.readthedocs.io/en/latest/pixmap.html#Pixmap.__init__
            # https://pymupdf.readthedocs.io/en/latest/page.html#Page.getPixmap
            mat_0 = fitz.Matrix(1, 1)
            # New in PyMuPDF version 1.16.0, annots kwarg for whether to ignore them.
            pixmap = page_crop_image_list.getPixmap(matrix=fitz.Identity,
                                                    colorspace=colorspace,
                                                    clip=None, alpha=False)
            # Maybe pgm below??
            image_ppm = pixmap.getImageData("ppm")  # Make PPM image from pixmap for tkinter.
            return image_ppm

        def get_page(self, page_num, window_size, zoom=False, fit_screen=True):
            """Return a `tkinter.PhotoImage` or a PNG image for a document page number.
            - The `page_num` argument is a 0-based page number.
            - The `zoom` argument is the top-left of old clip rect, and one of -1, 0,
              +1 for dim. x or y to indicate the arrow key pressed.
            - The `max_size` argument is the (width, height) of available image area.
            """
            zoom_x = 1
            zoom_y = 1
            scale = fitz.Matrix(zoom_x, zoom_y)

            page_display_list = self.page_display_list_cache[page_num]
            if not page_display_list:  # Create if not yet there.
                self.page_display_list_cache[page_num] = self.document[page_num].getDisplayList()
                page_display_list = self.page_display_list_cache[page_num]

            rect = page_display_list.rect  # The page rectangle.
            clip = rect

            # Make sure that the image will fits the screen.
            zoom_0 = 1
            if window_size:
                zoom_0 = min(1, window_size[0] / rect.width, window_size[1] / rect.height)
                if zoom_0 == 1:
                    zoom_0 = min(window_size[0] / rect.width, window_size[1] / rect.height)
            mat_0 = fitz.Matrix(zoom_0, zoom_0)

            if zoom:
                w2 = rect.width / 2        # we need these ...
                h2 = rect.height / 2       # a few times
                clip = rect * 0.5          # clip rect size is a quarter page
                tl = zoom[0]               # old top-left
                tl.x += zoom[1] * (w2 / 2) # adjust top-left ...
                tl.x = max(0, tl.x)        # according to ...
                tl.x = min(w2, tl.x)       # arrow key ...
                tl.y += zoom[2] * (h2 / 2) # provided, but ...
                tl.y = max(0, tl.y)        # stay within ...
                tl.y = min(h2, tl.y)       # the page rect
                clip = fitz.Rect(tl, tl.x + w2, tl.y + h2)

                # Clip rect is ready, now fill it.
                mat = mat_0 * fitz.Matrix(2, 2)  # The zoom matrix.
                pixmap = page_display_list.getPixmap(alpha=False, matrix=mat, clip=clip)

            else:  # Show the total page.
                pixmap = page_display_list.getPixmap(matrix=mat_0, alpha=False)

            image_ppm = pixmap.getImageData("ppm")  # Make PPM image from pixmap for tkinter.

            return image_ppm, clip.tl  # Return image, clip position.


""" 
 @file
 @brief This file contains the project file listview, used by the main window
 @author Noah Figg <eggmunkee@hotmail.com>
 @author Jonathan Thomas <jonathan@openshot.org>
 
 @section LICENSE
 
 Copyright (c) 2008-2016 OpenShot Studios, LLC
 (http://www.openshotstudios.com). This file is part of
 OpenShot Video Editor (http://www.openshot.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.
 
 OpenShot Video Editor is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 OpenShot Video Editor is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 
 You should have received a copy of the GNU General Public License
 along with OpenShot Library.  If not, see <http://www.gnu.org/licenses/>.
 """

import os
from urllib.parse import urlparse

from PyQt5.QtCore import QSize, Qt, QPoint
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QListView, QMessageBox, QAbstractItemView, QMenu
import openshot  # Python module for libopenshot (required video editing module installed separately)

from classes.logger import log
from classes.query import File
from classes.app import get_app
from windows.models.files_model import FilesModel

try:
    import json
except ImportError:
    import simplejson as json


class FilesListView(QListView):
    """ A ListView QWidget used on the main window """
    drag_item_size = 48

    def updateSelection(self):
        log.info('updateSelection')

        # Track selected items
        self.selected = self.selectionModel().selectedIndexes()

        # Track selected file ids on main window
        rows = []
        self.win.selected_files = []
        for selection in self.selected:
            selected_row = self.files_model.model.itemFromIndex(selection).row()
            if selected_row not in rows:
                self.win.selected_files.append(self.files_model.model.item(selected_row, 5).text())
                rows.append(selected_row)

    def contextMenuEvent(self, event):
        # Update selection
        self.updateSelection()

        # Set context menu mode
        app = get_app()
        app.context_menu_object = "files"

        menu = QMenu(self)

        menu.addAction(self.win.actionImportFiles)
        menu.addSeparator()
        if self.selected:
            # If file selected, show file related options
            menu.addAction(self.win.actionPreview_File)
            menu.addAction(self.win.actionSplitClip)
            menu.addAction(self.win.actionAdd_to_Timeline)
            menu.addSeparator()
            #menu.addAction(self.win.actionFile_Properties)
            menu.addAction(self.win.actionRemove_from_Project)
            menu.addSeparator()
        menu.addAction(self.win.actionDetailsView)

        # Show menu
        menu.exec_(QCursor.pos())

    def dragEnterEvent(self, event):
        # If dragging urls onto widget, accept
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()

    def startDrag(self, event):
        """ Override startDrag method to display custom icon """

        # Get image of selected item
        selected_row = self.files_model.model.itemFromIndex(self.selectionModel().selectedIndexes()[0]).row()
        icon = self.files_model.model.item(selected_row, 0).icon()

        # Start drag operation
        drag = QDrag(self)
        drag.setMimeData(self.files_model.model.mimeData(self.selectionModel().selectedIndexes()))
        # drag.setPixmap(QIcon.fromTheme('document-new').pixmap(QSize(self.drag_item_size,self.drag_item_size)))
        drag.setPixmap(icon.pixmap(QSize(self.drag_item_size, self.drag_item_size)))
        drag.setHotSpot(QPoint(self.drag_item_size / 2, self.drag_item_size / 2))
        drag.exec_()

    # Without defining this method, the 'copy' action doesn't show with cursor
    def dragMoveEvent(self, event):
        pass

    def is_image(self, file):
        path = file["path"].lower()

        if path.endswith((".jpg", ".jpeg", ".png", ".bmp", ".svg", ".thm", ".gif", ".bmp", ".pgm", ".tif", ".tiff")):
            return True
        else:
            return False

    def add_file(self, filepath):
        path, filename = os.path.split(filepath)

        # Add file into project
        app = get_app()

        # Check for this path in our existing project data
        file = File.get(path=filepath)

        # If this file is already found, exit
        if file:
            return

        # Load filepath in libopenshot clip object (which will try multiple readers to open it)
        clip = openshot.Clip(filepath)

        # Get the JSON for the clip's internal reader
        try:
            reader = clip.Reader()
            file_data = json.loads(reader.Json())

            # Determine media type
            if file_data["has_video"] and not self.is_image(file_data):
                file_data["media_type"] = "video"
            elif file_data["has_video"] and self.is_image(file_data):
                file_data["media_type"] = "image"
            elif file_data["has_audio"] and not file_data["has_video"]:
                file_data["media_type"] = "audio"

            # Save new file to the project data
            file = File()
            file.data = file_data
            file.save()
            return True

        except:
            # Handle exception
            msg = QMessageBox()
            msg.setText(app._tr("{} is not a valid video, audio, or image file.".format(filename)))
            msg.exec_()
            return False

    # Handle a drag and drop being dropped on widget
    def dropEvent(self, event):
        # log.info('Dropping file(s) on files tree.')
        for uri in event.mimeData().urls():
            file_url = urlparse(uri.toString())
            if file_url.scheme == "file":
                filepath = file_url.path
                if filepath[0] == "/" and ":" in filepath:
                    filepath = filepath[1:]
                if os.path.exists(filepath.encode('UTF-8')) and os.path.isfile(filepath.encode('UTF-8')):
                    log.info('Adding file: {}'.format(filepath))
                    if self.add_file(filepath):
                        event.accept()

    def clear_filter(self):
        if self:
            self.win.filesFilter.setText("")

    def filter_changed(self):
        if self:
            if self.win.filesFilter.text() == "":
                self.win.actionFilesClear.setEnabled(False)
            else:
                self.win.actionFilesClear.setEnabled(True)
            self.refresh_view()

    def refresh_view(self):
        self.files_model.update_model()

    def resize_contents(self):
        pass

    def __init__(self, *args):
        # Invoke parent init
        QListView.__init__(self, *args)

        # Get a reference to the window object
        self.win = get_app().window

        # Get Model data
        self.files_model = FilesModel()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.selected = []

        # Setup header columns
        self.setModel(self.files_model.model)
        self.setIconSize(QSize(131, 108))
        self.setViewMode(QListView.IconMode)
        self.setResizeMode(QListView.Adjust)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setUniformItemSizes(True)
        self.setWordWrap(True)
        self.setStyleSheet('QListView::item { padding-top: 2px; }')

        # Refresh view
        self.refresh_view()

        # setup filter events
        app = get_app()
        app.window.filesFilter.textChanged.connect(self.filter_changed)
        app.window.actionFilesClear.triggered.connect(self.clear_filter)

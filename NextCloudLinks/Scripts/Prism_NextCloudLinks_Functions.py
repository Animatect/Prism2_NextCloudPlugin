# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_NextCloudLinks_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.core.popup("Custom code executed successfully!")
        self.core.callbacks.registerCallback("openPBListContextMenu", self.prueba, plugin=self)
        self.core.callbacks.registerCallback("mediaPlayerContextMenuRequested", self.prueba2, plugin=self)
        #self.core.plugins.monkeyPatch(self.core.mediaBrowser.getMediaPreviewMenu, self.custom_getMediaPreviewMenu, self, force=True)

    def prueba(self, origin, rcmenu, lw, item, path):
        #if lw == origin.lw_version:  # Solo si es el widget de versiones
        nueva_accion = QAction("Acción de ejemplo", origin)
        nueva_accion.triggered.connect(lambda: self.mi_funcion(path))
        rcmenu.addAction(nueva_accion)

    def prueba2(self, origin, menu):
        if not menu:
            return
        
        nueva_accion2 = QAction("Acción de ejemplo2", origin)
        nueva_accion2.triggered.connect(lambda: self.mi_funcion2("Vista previa"))
        menu.addAction(nueva_accion2)
     
    def mi_funcion(self, path):
        print(f"Acción ejecutada para: {path}")

    def mi_funcion2(self, context):
        print(f"Acción ejecutada desde: {context}")

       

    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True
    


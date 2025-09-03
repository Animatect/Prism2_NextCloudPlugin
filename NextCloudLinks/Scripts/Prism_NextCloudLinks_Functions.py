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
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import json
import sys
import base64
import hashlib
from itertools import cycle

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_NextCloudLinks_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.core.registerCallback("projectBrowser_loadUI", self.nextcloudTabLinksEdit, plugin=self)
        self.core.registerCallback("userSettings_loadUI", self.userSettings_Nextcloud, plugin=self)
        self.core.callbacks.registerCallback("openPBListContextMenu", self.nextButton, plugin=self)
        self.core.callbacks.registerCallback("mediaPlayerContextMenuRequested", self.nextButtonPreview, plugin=self)
        self.nextcloud_user, self.nextcloud_password, self.nextcloud_url = self.load_nextcloud_credentials()
        self.core.registerCallback("onMediaBrowserOpen", self.onMediaBrowserOpen, plugin=self)

    def nextcloudTabLinksEdit(self, projectBrowser):

        class NextcloudTabWidget(QWidget):
            def __init__(self, plugin, parent=None):
                super().__init__(parent)
                self.plugin = plugin
                self.layout = QVBoxLayout()
                self.setLayout(self.layout)
                
                # Crear tabla
                self.table = QTableWidget(0, 4)
                self.table.setHorizontalHeaderLabels(["Ruta", "Enlace", "Permisos", "Expiración"])
                self.table.verticalHeader().setVisible(False)
                self.table.setEditTriggers(QTableWidget.NoEditTriggers)
                self.table.setSelectionBehavior(QTableWidget.SelectRows)
                self.layout.addWidget(self.table)
                
                # Botón de actualizar
                self.refresh_btn = QPushButton("Actualizar")
                self.refresh_btn.clicked.connect(self.load_data)
                self.layout.addWidget(self.refresh_btn)

            def refreshUI(self):
                self.load_data

            def getSelectedContext(self):
                return None
                
            def entered(self, prevTab=None, navData=None):
                print("Pestaña Nextcloud activada - Cargando enlaces...")
                self.load_data()
                
            def load_data(self):
                # Limpiar tabla
                self.table.setRowCount(0)
                
                # Obtener datos
                shares = self.plugin.get_all_project_public_shares()
                
                # Llenar tabla
                for share in shares:
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    
                    # Convertir permisos a texto
                    permissions_value = share.get('permissions', '')
                    if permissions_value in ['1', '17']:
                        permissions_text = 'Lectura'
                    elif permissions_value in ['15', '23', '31']:
                        permissions_text = 'Lectura/Escritura'
                    else:
                        permissions_text = f'Custom ({permissions_value})'
                    
                    self.table.setItem(row, 0, QTableWidgetItem(share.get('path', '')))
                    self.table.setItem(row, 1, QTableWidgetItem(share.get('url', '')))
                    self.table.setItem(row, 2, QTableWidgetItem(permissions_text))
                    self.table.setItem(row, 3, QTableWidgetItem(share.get('expiration', '')))
                
                self.table.resizeColumnsToContents()
                
                # Conectar doble click para copiar URL
                self.table.doubleClicked.connect(self.copy_selected_link)
            
            def copy_selected_link(self, index):
                if index.column() == 1:  # Columna de URL
                    url = self.table.item(index.row(), 1).text()
                    self.parent().plugin.core.copyToClipboard(url, file=False)
                    self.parent().plugin.core.popup(f"Enlace copiado:\n{url}")

        # Usar la clase personalizada
        custom_tabNextcloud = NextcloudTabWidget(self)
        #custom_layout = QVBoxLayout(custom_tabNextcloud)
        #custom_layout.addWidget(QLabel("Contenido de ejemplo"))
        
        #test_button = QPushButton("Ejecutar acción")
        #test_button.clicked.connect(self.handleCustomAction)
        #custom_layout.addWidget(test_button)
        
        # Añadir la pestaña al proyecto browser
        custom_tabNextcloud.setProperty("tabType", "custom")
        projectBrowser.addTab("Nextcloud", custom_tabNextcloud)

    def get_all_project_public_shares(self):
                remote_root = self.get_remote_root()
                
                endpoint = f"{self.nextcloud_url.rstrip('/')}/ocs/v2.php/apps/files_sharing/api/v1/shares"
                headers = {
                    "OCS-APIRequest": "true",
                    "Accept": "application/json"
                }

                try:
                    response = requests.get(
                        endpoint,
                        headers=headers,
                        auth=(self.nextcloud_user, self.nextcloud_password),
                        timeout=30
                    )

                    if response.status_code != 200:
                        self.core.writeErrorLog(f"Error getting all shares: HTTP {response.status_code}", response.text)
                        return []

                    shares = response.json().get('ocs', {}).get('data', [])
                    project_shares = []
                    
                    for share in shares:
                        share_type = str(share.get('share_type', ''))
                        if share_type != '3':  # Solo shares públicos
                            continue

                        share_path = share.get('path', '')
                        # Filtrar por rutas dentro del proyecto actual
                        if share_path.startswith(remote_root):
                            permissions_value = str(share.get('permissions', ''))
                            expiration = share.get('expiration', '')
                            if not expiration:
                                expiration = 'Sin duración limite'

                            project_shares.append({
                                'url': share.get('url', ''),
                                'permissions': permissions_value,
                                'expiration': expiration,
                                'path': share_path
                            })

                    return project_shares

                except Exception as e:
                    self.core.writeErrorLog("Error getting all project public shares", str(e))
                    return []
                

    def onMediaBrowserOpen(self, mediaBrowser):

        current_file = None
        try:
            if hasattr(mediaBrowser, "getCurrentFile"):
                current_file = mediaBrowser.getCurrentFile()
                print(f"Archivo actual: {current_file}")
            elif hasattr(mediaBrowser, "mediaPlayer") and hasattr(mediaBrowser.mediaPlayer, "getCurrentFile"):
                current_file = mediaBrowser.mediaPlayer.getCurrentFile()
                print(f"Archivo actual desde mediaPlayer: {current_file}")
            else:
                print("No se encontró método para obtener archivo actual")
        except Exception as e:
            print(f"Error al obtener archivo actual: {str(e)}")

        # También puedes inspeccionar todos los renders si están disponibles
        try:
            if hasattr(mediaBrowser, "getAllRenders"):
                renders = mediaBrowser.getAllRenders()
                print("Renders encontrados:")
                for r in renders:
                    path = r.get("path", "")
                    print(f" - {path}")
            elif hasattr(mediaBrowser, "mediaPlayer") and hasattr(mediaBrowser.mediaPlayer, "getAllRenders"):
                renders = mediaBrowser.mediaPlayer.getAllRenders()
                print("Renders desde mediaPlayer:")
                for r in renders:
                    path = r.get("path", "")
                    print(f" - {path}")
            else:
                print("No se encontró método para obtener renders")
        except Exception as e:
            print(f"Error al obtener renders: {str(e)}")
        print("Atributos de mediaBrowser:")
        for attr in dir(mediaBrowser):
            if not attr.startswith('__'):
                print(f"  {attr}: {getattr(mediaBrowser, attr)}")
        print("\nLayouts encontrados:")
        for child in mediaBrowser.children():
            if isinstance(child, QLayout):
                print(f"  {type(child).__name__}: {child}")
        try:
            labels = mediaBrowser.findChildren(QLabel)
            aovs_label = None
            
            # Buscar la etiqueta con texto "AOVs:"
            for label in labels:
                if label.text() == "AOVs:":
                    aovs_label = label
                    break
            
            if aovs_label is None:
                print("No se encontró la etiqueta 'AOVs:'")
                return
            
            # Obtener el layout padre de la etiqueta AOVs
            parent_layout = aovs_label.parent().layout()
            
            if parent_layout is None:
                print("No se pudo encontrar el layout padre")
                return
            
            # Encontrar el índice de la etiqueta AOVs en el layout
            index = parent_layout.indexOf(aovs_label)
            
            if index == -1:
                print("No se pudo encontrar el índice de la etiqueta AOVs")
                return
            nueva_etiqueta =QPushButton("Nextcloud")
            #nueva_etiqueta.setAlignment(Qt.AlignCenter)
            nueva_etiqueta.setStyleSheet("background-color: #2C2C2C; color: #FFFFFF; padding: 5px;")
            
            parent_layout.insertWidget(index, nueva_etiqueta)

                
        except Exception as e:
            print(f"Error al añadir etiqueta estática: {str(e)}")
            import traceback
            traceback.print_exc()


    def showInfoMessage(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(message)
        msg.setWindowTitle("Prism")
        msg.exec_()

    def get_remote_root(self):
        project_path = self.core.projectPath
        if not project_path:
            return "/PROYECTOS"
        
        project_path = os.path.abspath(project_path)
        parts = project_path.split(os.sep)
        parts_lower = [p.lower() for p in parts]
        
        if "proyectos" in parts_lower:
            idx = parts_lower.index("proyectos")
            relative_project_path = os.sep.join(parts[idx+1:])
            return "/PROYECTOS/" + relative_project_path.replace(os.sep, '/')
        else:
            project_name = os.path.basename(project_path)
            return "/PROYECTOS/" + project_name

    def nextButton(self, origin, rcmenu, lw, item, path):
        nextcloudButton = QAction("Compartir por Nextcloud", origin)
        iconPath = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Icons",
            "logo_nextcloud.png"
        )
        if not os.path.exists(iconPath):
            self.showInfoMessage(f"Icono no encontrado en: {iconPath}")
        
        icon = self.core.media.getColoredIcon(iconPath)
        nextcloudButton.setIcon(icon)
        nextcloudButton.triggered.connect(lambda: self.showNextcloudShareMenu(path))
        rcmenu.addAction(nextcloudButton)

        nextcloudLinkList = QAction("Links generados", origin)
        nextcloudLinkList.triggered.connect(lambda: self.show_public_links_list(path))
        rcmenu.addAction(nextcloudLinkList)

    def nextButtonPreview(self, origin, menu):
        if not menu:
            return
        
        contexts = origin.getCurRenders()
        if not contexts or not contexts[0].get("path"):
            return
        
        path = contexts[0]["path"]

        if hasattr(origin, "seq") and len(origin.seq) == 1:
            path = os.path.join(path, origin.seq[0])
        
        nextcloudButtonPreview = QAction("Compartir por Nextcloud", origin)
        iconPath = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Icons",
            "logo_nextcloud.png"
        )
        if not os.path.exists(iconPath):
            self.showInfoMessage(f"Icono no encontrado en: {iconPath}")
        
        icon = self.core.media.getColoredIcon(iconPath)
        nextcloudButtonPreview.setIcon(icon)
        nextcloudButtonPreview.triggered.connect(lambda: self.showNextcloudShareMenu(path))
        menu.addAction(nextcloudButtonPreview)

        nextcloudLinkListPreview = QAction("Links generados", origin)
        nextcloudLinkListPreview.triggered.connect(lambda: self.show_public_links_list(path))
        menu.addAction(nextcloudLinkListPreview)

    def showNextcloudShareMenu(self, path):
        # Crear el menú de configuración
        share_menu = QMenu("Configuración de Nextcloud")

        # Almacenar los valores del combobox
        permisos_combo = None
        duracion_combo = None

        # Añadir título como primera acción (no clickable)
        title_action = QWidgetAction(share_menu)
        title_widget = QLabel("<b>Configuración del link</b>")
        title_widget.setMargin(5)  # Añadir un poco de espacio
        title_action.setDisabled(True)  # Hacerlo no clickable
        title_action.setDefaultWidget(title_widget)
        share_menu.addAction(title_action)
        share_menu.addSeparator()
        
        
        def create_option_widget(label_text):
            nonlocal permisos_combo, duracion_combo
            widget = QWidgetAction(share_menu)
            container = QWidget()
            layout = QHBoxLayout()
            label = QLabel(label_text)

            # Combo box
            combo = QComboBox()
            if label_text == "Permisos":
                combo.addItems(["ONLY READ", "EDIT"])
                permisos_combo = combo
            elif label_text == "Duración del link":
                combo.addItems(["1 DAY", "1 MONTH", "6 MONTHS", "ALWAYS"])
                duracion_combo = combo
            
            # Añadir al layout
            layout.addWidget(label)
            layout.addWidget(combo)
            container.setLayout(layout)
            widget.setDefaultWidget(container)
            return widget
    
        # Añadir opciones al menú
        share_menu.addAction(create_option_widget("Permissions"))
        share_menu.addAction(create_option_widget("Link duration"))
        share_menu.addSeparator()

        accept_action = QWidgetAction(share_menu)
        accept_widget = QPushButton("Generate link")

        def on_generate_clicked():
            # Obtener los valores seleccionados
            permisos = permisos_combo.currentText() if permisos_combo else "READ ONLY"
            duracion = duracion_combo.currentText() if duracion_combo else "1 día"

            # Convertir a valores validos para la api de nextcloud
            permisos_value = "1" if permisos == "READ ONLY" else "23"

            if duracion == "1 día":
                expire_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            elif duracion == "1 mes":
                expire_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            elif duracion == "6 meses":
                expire_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
            elif duracion == "Siempre":
                expire_date = None
            else:
                expire_date =(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

            self.generar_y_copiar_enlace(path, permisos_value, expire_date)
            share_menu.close()

        accept_widget.clicked.connect(on_generate_clicked)        
        
        accept_action.setDefaultWidget(accept_widget)
        share_menu.addAction(accept_action)

        # Mostrar el menú en la posición del cursor
        share_menu.exec_(QCursor.pos())    
    
    def generar_y_copiar_enlace(self, path, permissions="1", expire_date=None):
        try:
            enlace = self.generar_enlace_nextcloud(path, permissions, expire_date)
            if enlace:
                self.core.copyToClipboard(enlace, file=False)
                self.showInfoMessage(f"Enlace copiado:\n{enlace}")
        except Exception as e:
            self.showInfoMessage(f"Error inesperado: {str(e)}")
            self.showInfoMessage("Nextcloud UI Error", str(e))

    def ruta_local_a_ruta_nextcloud(self, path):
        # Normalizar rutas para comparación segura
        project_path = self.core.projectPath
        project_path = os.path.abspath(project_path)
        abs_path = os.path.abspath(path)
        
        if not abs_path.startswith(project_path):
            error_msg = (
                "Error: La ruta no está dentro del directorio Nextcloud\n"
                f"Directorio Nextcloud: {project_path}\n"
                f"Ruta seleccionada: {abs_path}"
            )
            self.showInfoMessage(error_msg)
            return None
        
        nextcloud_remote_root = self.get_remote_root()
        rel_path = os.path.relpath(abs_path, project_path)
        nc_path = nextcloud_remote_root + "/" + rel_path.replace('\\', '/').lstrip('/')
        return nc_path.replace("//", "/")

    def generar_enlace_nextcloud(self, path, permissions="1", expire_date=None):
        # Verificar credenciales primero
        cred_errors = []
        if not self.nextcloud_url: 
            cred_errors.append("URL de Nextcloud no configurada")
        if not self.nextcloud_user: 
            cred_errors.append("Usuario de Nextcloud no configurado")
        if not self.nextcloud_password: 
            cred_errors.append("Contraseña de Nextcloud no configurada")
        
        if cred_errors:
            error_msg = "Configuración incompleta:\n" + "\n".join(cred_errors)
            self.showInfoMessage(error_msg)
            return None 

        # Verificar si el path es válido
        if not path or not os.path.exists(path):
            self.showInfoMessage(f"Ruta inválida o no existe:\n{path}")
            return None

        try:
            nc_path = self.ruta_local_a_ruta_nextcloud(path)
            if not nc_path:
                return None

        except Exception as e:
            self.showInfoMessage(f"Error al convertir ruta:\n{str(e)}")
            return None
        
        # Verificar shares existentes para este recurso
        existing_share = self._get_existing_share(nc_path, permissions, expire_date)
        if existing_share:
            return existing_share
        
        return self._create_new_share(nc_path, permissions, expire_date)
        
    def _get_existing_share(self, nc_path, desired_permissions, desired_expire_date=None):    
        # Busca shares existentes que coincidan con los parámetros deseados
        try:
            import urllib.parse
            encoded_path = urllib.parse.quote(nc_path)
        except:
            encoded_path = nc_path
        
        endpoint = f"{self.nextcloud_url.rstrip('/')}/ocs/v2.php/apps/files_sharing/api/v1/shares?path={encoded_path}&reshares=true"
        headers = {
            "OCS-APIRequest": "true",
            "Accept": "application/json"
        }

        try:
            # Enviar solicitud
            response = requests.get(
                endpoint,
                headers=headers,
                auth=(self.nextcloud_user, self.nextcloud_password),
                timeout=20
            )

            # 6. Procesar respuesta
            if response.status_code != 200:
                return None
            
            try:
                data = response.json()
                shares = data.get('ocs', {}).get('data', [])
            except ValueError:
                # Si falla el JSON, intentar parsear como XML
                try:
                    root = ET.fromstring(response.content)
                    shares = []
                    for element in root.findall('.//element'):
                        share_data = {}
                        for child in element:
                            if child.tag == 'id':
                                share_data['id'] = child.text
                            elif child.tag == 'share_type':
                                share_data['share_type'] = child.text
                            elif child.tag == 'permissions':
                                share_data['permissions'] = child.text
                            elif child.tag == 'url':
                                share_data['url'] = child.text
                            elif child.tag == 'expiration':
                                share_data['expiration'] = child.text
                        shares.append(share_data)
                except ET.ParseError:
                    self.core.writeErrorLog("Nextcloud API Response Parse Error", "Could not parse response as JSON or XML")
                    return None

            public_shares = [s for s in shares if str(s.get('share_type')) == '3']
            
            for share in public_shares:
                # Comparar permisos
                current_permissions = str(share.get('permissions', 0))
                if current_permissions != desired_permissions:  # 17 es lectura + compartir
                    continue
                current_expire = share.get('expiration', '')
                if desired_expire_date is None:
                    if current_expire:
                        continue
                else:
                    if not current_expire:
                        continue
                    if not current_expire.startswith(desired_expire_date):
                        continue
                return share.get('url', '')
            
        except Exception as e:
            self.core.writeErrorLog("Error checking existing shares", str(e))
        
        return None
    
    def _create_new_share(self, nc_path, permissions, expire_date=None):
        # Crear nuevo share
        endpoint = f"{self.nextcloud_url.rstrip('/')}/ocs/v2.php/apps/files_sharing/api/v1/shares"
        headers = {
            "OCS-APIRequest": "true",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {
            "path": nc_path,
            "shareType": "3",  # Enlace público
            "permissions": permissions
        }
        
        if expire_date:
            data["expireDate"] = expire_date

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                data=data,
                auth=(self.nextcloud_user, self.nextcloud_password),
                timeout=20
            )

            if response.status_code != 200:
                error_msg = (f"Error en la API (HTTP {response.status_code}):\n"
                            f"Respuesta: {response.text[:200]}{'...' if len(response.text) > 200 else ''}")
                self.core.writeErrorLog("Nextcloud API Error", error_msg)
                self.showInfoMessage(error_msg)
                return None
            
            try:
                json_data = response.json()
                url = json_data.get('ocs', {}).get('data', {}).get('url', '')
                if url:
                    return url
            
            except ValueError:
                root = ET.fromstring(response.content)
                url_element = root.find('.//ns:url', namespaces) or root.find('.//url')
                if url_element is not None and url_element.text:
                    return url_element.text
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión: {str(e)}"
            self.showInfoMessage(error_msg)
            self.core.writeErrorLog("Connection Error", error_msg)
        except ET.ParseError:
            error_msg = "Error al analizar respuesta XML"
            self.showInfoMessage(error_msg)
            self.core.writeErrorLog("XML Parse Error", error_msg)
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            self.showInfoMessage(error_msg)
            self.core.writeErrorLog("Unexpected Error", error_msg)
            
        self.showInfoMessage(f"No se pudo extraer el enlace de la respuesta")
        return None    

    # Mostrar los links ya generados 
    def show_public_links_list(self, path):
        #Muestra diálogo con todos los enlaces públicos del recurso
        
        try:
            if not path or not os.path.exists(path):
                return
            
            nc_path = self.ruta_local_a_ruta_nextcloud(path)
            if not nc_path:
                return
            
            all_public_shares = self._get_all_public_shares(nc_path)
            
            if not all_public_shares:
                self.showInfoMessage(f"Info: No hay enlaces públicos para este recurso")
                return

            dialog = QDialog()
            dialog.setWindowTitle("Enlaces Públicos Existentes")
            dialog.setMinimumWidth(600)
            
            layout = QVBoxLayout()
            
            # Creación de tabla
            table = QTableWidget(0, 3)
            table.setHorizontalHeaderLabels(["Link", "Permissions", "Caduce"])
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            
            # Llenado de tabla
            for share in all_public_shares:
                row = table.rowCount()
                table.insertRow(row)
                
                url = share.get('url', '')
                permissions_value = share.get('permissions', '')
                if permissions_value in ['1', '17']:
                    permissions_text = 'READ'
                elif permissions_value in ['15', '23', '31']:
                    permissions_text = 'READ/WRITE'
                else:
                    permissions_text = f'Desconocido ({permissions_value})'
                expiration = share.get('expiration', 'No caduce')
                
                table.setItem(row, 0, QTableWidgetItem(url))
                table.setItem(row, 1, QTableWidgetItem(permissions_text))
                table.setItem(row, 2, QTableWidgetItem(expiration))
            
            table.resizeColumnsToContents()
            
            # Botón para copiar
            btn_copy = QPushButton("Copiar seleccionado")
            btn_copy.clicked.connect(lambda: self._copy_from_table(table))
            
            # Organizar layout
            layout.addWidget(table)
            layout.addWidget(btn_copy)
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            error_msg = f"Error crítico:\n{str(e)}"
            self.showInfoMessage(error_msg)
            self.core.writeErrorLog("Error en show_public_links_list", str(e))

    def _get_all_public_shares(self, nc_path):
        #Obtiene todos los shares públicos existentes para un recurso
        endpoint = f"{self.nextcloud_url.rstrip('/')}/ocs/v2.php/apps/files_sharing/api/v1/shares?path={nc_path}&reshares=true"
        headers = {
            "OCS-APIRequest": "true",
            "Accept": "application/json"
        }

        try:
            response = requests.get(
                endpoint,
                headers=headers,
                auth=(self.nextcloud_user, self.nextcloud_password),
                timeout=20
            )
            
            if response.status_code != 200:
                error_msg = f"Error en la API (HTTP {response.status_code}):\n{response.text[:200]}"
                self.showInfoMessage(error_msg)
                return []
            
            shares = response.json().get('ocs', {}).get('data', [])
            public_shares = []
            for share in shares:
                share_type = str(share.get('share_type', ''))
                permissions = str(share.get('permissions', ''))
                
                if share_type == '3':
                    expiration = share.get('expiration', '')
                    if not expiration:
                        expiration = 'Sin duración limite'

                    public_shares.append({
                        'url': share.get('url', ''),
                        'permissions': permissions,
                        'expiration': expiration,
                        'id': share.get('id', '')
                    })
            
            return public_shares
            
        except Exception as e:
            error_msg = f"Error al obtener shares:\n{str(e)}"
            self.showInfoMessage(error_msg)
            self.core.writeErrorLog("Error getting public shares", str(e))
            return []

    def _copy_from_table(self, table):
        #Copia el enlace seleccionado con verificación
        selected = table.selectedItems()
        
        if not selected:

            return
        
        url = selected[0].text()
        if not url:
        
            return
        
        self.core.copyToClipboard(url, file=False)
        self.showInfoMessage(f"Enlace copiado:\n{url}")

    # Para añadir a settings
    def userSettings_Nextcloud(self, origin):
        origin.w_nextcloud = QWidget()
        origin.lo_nextcloud = QVBoxLayout(origin.w_nextcloud)
        origin.gb_credentials = QGroupBox("Nextcloud Credentials")
        origin.lo_credentials = QFormLayout(origin.gb_credentials)
        
        # Campo para nombre de usuario
        origin.le_username = QLineEdit()
        origin.le_username.setPlaceholderText("Enter your Nextcloud username")
        origin.lo_credentials.addRow("Username:", origin.le_username)
        
        # Campo para contraseña
        origin.le_password = QLineEdit()
        origin.le_password.setPlaceholderText("Enter your Nextcloud password")
        origin.le_password.setEchoMode(QLineEdit.Password)  # Oculta los caracteres
        origin.lo_credentials.addRow("Password:", origin.le_password)
        
        # Campo para url de nextcloud
        origin.le_url = QLineEdit()
        origin.le_url.setPlaceholderText("Enter the url to nextcloud")
        origin.lo_credentials.addRow("URL:", origin.le_url)
        
        # Botón para guardar credenciales
        origin.btn_save = QPushButton("Save Credentials")
        origin.btn_save.clicked.connect(lambda: self.save_nextcloud_credentials(
            origin.le_username.text(),
            origin.le_password.text(),
            origin.le_url.text()
        ))
        
        origin.lo_nextcloud.addWidget(origin.gb_credentials)
        origin.lo_nextcloud.addWidget(origin.btn_save)
        sp_stretch = QSpacerItem(0, 0, QSizePolicy.Fixed, QSizePolicy.Expanding)
        origin.lo_nextcloud.addItem(sp_stretch)
        
        # Añadir la pestaña a los ajustes de usuario
        origin.addTab(origin.w_nextcloud, "Nextcloud")

        # Cargar credenciales guardadas
        username, password, url = self.load_nextcloud_credentials()
        origin.le_username.setText(username)
        origin.le_password.setText(password)
        origin.le_url.setText(url)

        pass
    
    def encrypt_password(self, text, key):
        if not text:
            return ""
        encrypted_bytes = [ord(c) ^ ord(k) for c, k in zip(text, cycle(key))]
        return base64.b64encode(bytes(encrypted_bytes)).decode('utf-8')
    
    def desencrypt_password(self, encrypted_text, key):
        if not encrypted_text:
            return ""
        try:
            encrypted_bytes = base64.b64decode(encrypted_text.encode('utf-8'))
            decrypted_bytes = [b ^ ord(k) for b, k in zip(encrypted_bytes, cycle(key))]
            return ''.join(chr(b) for b in decrypted_bytes)
        except:
            return encrypted_text
        
    def get_encryption_key(self):
        system_info = os.path.join(os.path.expanduser("~"), os.name, sys.platform)
        return hashlib.sha256(system_info.encode()).hexdigest()[:16]

    def save_nextcloud_credentials(self, username, password, url):
        if not all([username, password, url]):
            self.showInfoMessage("Error: The url, username and password cannot be empty")
            return
        
        try:
            encryption_key = self.get_encryption_key()
            encrypted_password = self.encrypt_password(password, encryption_key)
            # La ruta del archivo JSON
            config_file = self.core.getUserPrefConfigPath()
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
            else:
                config_data = {}
            # Definir la estructura de datos a guardar
            config_data["Nextcloud_credentials"] = {
                "nextcloud_username": username,
                "nextcloud_password": encrypted_password,
                "nextcloud_url": url
            }

            # Guardar en archivo JSON
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            print("Credentials saved successfully!")
            
            # Actualizar la configuración actual
            self.nextcloud_user = username
            self.nextcloud_password = password
            self.nextcloud_url = url
            
        except Exception as e:
            self.showInfoMessage(f"Error saving credentials: {str(e)}")

    def load_nextcloud_credentials(self):
        #Función para cargar las credenciales desde el archivo json"
        try:
            config_file = self.core.getUserPrefConfigPath()
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                credentials = config_data.get("Nextcloud_credentials", {})
                username = credentials.get("nextcloud_username", "")
                encrypted_password = credentials.get("nextcloud_password", "")
                url = credentials.get("nextcloud_url", "")
                encryption_key = self.get_encryption_key()
                password = self.desencrypt_password(encrypted_password, encryption_key)
                return (username, password, url)
        
        except Exception as e:
            print(f"Error loading credentials: {str(e)}")
        
        return ("", "", "")

    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True
    


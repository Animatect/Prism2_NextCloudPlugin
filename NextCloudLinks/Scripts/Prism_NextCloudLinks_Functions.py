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

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_NextCloudLinks_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.core.popup("Custom code executed successfully!")
        self.core.registerCallback("userSettings_loadUI", self.userSettings_Nextcloud, plugin=self)
        self.core.callbacks.registerCallback("openPBListContextMenu", self.nextButton, plugin=self)
        self.core.callbacks.registerCallback("mediaPlayerContextMenuRequested", self.nextButtonPreview, plugin=self)
        self.nextcloud_user, self.nextcloud_password, self.nextcloud_url = self.load_nextcloud_credentials()

    def nextButton(self, origin, rcmenu, lw, item, path):
        nextcloudButton = QAction("Compartir por Nextcloud", origin)
        iconPath = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Icons",
            "logo_nextcloud.png"
        )
        if not os.path.exists(iconPath):
            self.core.popup(f"Icono no encontrado en: {iconPath}")
        
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
        
        path = contexts[0]["path"]

        if hasattr(origin, "seq") and len(origin.seq) == 1:
            path = os.path.join(path, origin.seq[0])
        
        nextcloudButtonPreview = QAction("Acción de ejemplo2", origin)
        iconPath = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Icons",
            "logo_nextcloud.png"
        )
        if not os.path.exists(iconPath):
            self.core.popup(f"Icono no encontrado en: {iconPath}")
        
        icon = self.core.media.getColoredIcon(iconPath)
        nextcloudButtonPreview.setIcon(icon)
        nextcloudButtonPreview.triggered.connect(lambda: self.showNextcloudShareMenu(path))
        menu.addAction(nextcloudButtonPreview)

        nextcloudLinkListPreview = QAction("Links generados", origin)
        nextcloudLinkListPreview.triggered.connect(lambda: self.show_public_links_list(path))
        menu.addAction(nextcloudLinkListPreview)
     
    def mi_funcion(self, path):
        print(f"Acción ejecutada para: {path}")
        print(f"url: {self.nextcloud_url}")
        print(f"user: {self.nextcloud_user}")
        print(f"contraseña: {self.nextcloud_password}")

    def mi_funcion2(self, context):
        print(f"Acción ejecutada desde: {context}")

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
                combo.addItems(["solo lectura", "edición"])
                permisos_combo = combo
            elif label_text == "Duración del link":
                combo.addItems(["24 horas", "1 semana"])
                duracion_combo = combo
            
            # Añadir al layout
            layout.addWidget(label)
            layout.addWidget(combo)
            container.setLayout(layout)
            widget.setDefaultWidget(container)
            return widget
    
        # Añadir opciones al menú
        share_menu.addAction(create_option_widget("Permisos"))
        share_menu.addAction(create_option_widget("Duración del link"))
        share_menu.addSeparator()

        accept_action = QWidgetAction(share_menu)
        accept_widget = QPushButton("Generar link")

        def on_generate_clicked():
            # Obtener los valores seleccionados
            permisos = permisos_combo.currentText() if permisos_combo else "solo lectura"
            duracion = duracion_combo.currentText() if duracion_combo else "24 horas"

            # Convertir a valores validos para la api de nextcloud
            permisos_value = "1" if permisos == "solo lectura" else "15"

            if duracion == "24 horas":
                expire_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                expire_date =(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

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
                self.core.popup(f"Enlace copiado:\n{enlace}")
            else:
                self.core.popup("No se pudo generar el enlace. Verifica los logs.")
        except Exception as e:
            self.core.popup(f"Error inesperado: {str(e)}")
            self.core.writeErrorLog("Nextcloud UI Error", str(e))

    def ruta_local_a_ruta_nextcloud(self, path):
        # Normalizar rutas para comparación segura
        local_root = os.path.abspath(self.nextcloud_local_root)
        abs_path = os.path.abspath(path)
        
        if not abs_path.startswith(local_root):
            error_msg = (
                "Error: La ruta no está dentro del directorio Nextcloud\n"
                f"Directorio Nextcloud: {local_root}\n"
                f"Ruta seleccionada: {abs_path}"
            )
            self.core.popup(error_msg)
            return None
        
        rel_path = os.path.relpath(abs_path, local_root)
        nc_path = "/tstProduction/" + rel_path.replace('\\', '/').lstrip('/')
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
            self.core.popup(error_msg)
            return None 

        # Verificar si el path es válido
        if not path or not os.path.exists(path):
            self.core.popup(f"Ruta inválida o no existe:\n{path}")
            return None

        try:
            nc_path = self.ruta_local_a_ruta_nextcloud(path)
            if not nc_path:
                return None

        except Exception as e:
            self.core.popup(f"Error al convertir ruta:\n{str(e)}")
            self.core.writeErrorLog("Nextcloud Path Conversion", str(e))
            return None
        
        # Verificar shares existentes para este recurso
        existing_share = self._get_existing_share(nc_path, permissions, expire_date)
        if existing_share:
            return existing_share
        
        return self._create_new_share(nc_path, permissions, expire_date)
        
    def _get_existing_share(self, nc_path, desired_permissions, desired_expire_date=None):    
        # Busca shares existentes que coincidan con los parámetros deseados
        endpoint = f"{self.nextcloud_url.rstrip('/')}/ocs/v2.php/apps/files_sharing/api/v1/shares?path={nc_path}&reshares=true"
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
            
            shares = response.json().get('ocs', {}).get('data', [])
            public_shares = [s for s in shares if str(s.get('share_type')) == '3']
            
            for share in public_shares:
                # Comparar permisos
                current_permissions = str(share.get('permissions', 0))
                if desired_permissions == "1":
                    if not (current_permissions & 1):
                        continue
                    if not (current_permissions & 2) or (current_permissions & 4) or (current_permissions & 8):
                        continue
                elif desired_permissions == "15":
                    if not (current_permissions & 1):
                        continue
                    if not (current_permissions & 2):
                        continue
                # Comparar fechas
                if desired_expire_date:
                    current_expire = share.get('expiration', '')
                    if current_expire and current_expire != desired_expire_date:
                        continue
                # Si el share coincide
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
                self.core.popup(error_msg)
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
            self.core.popup(error_msg)
            self.core.writeErrorLog("Connection Error", error_msg)
        except ET.ParseError:
            error_msg = "Error al analizar respuesta XML"
            self.core.popup(error_msg)
            self.core.writeErrorLog("XML Parse Error", error_msg)
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            self.core.popup(error_msg)
            self.core.writeErrorLog("Unexpected Error", error_msg)
            
        self.core.popup("No se pudo extraer el enlace de la respuesta")
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
                self.core.popup("Info: No hay enlaces públicos para este recurso")
                return

            dialog = QDialog()
            dialog.setWindowTitle("Enlaces Públicos Existentes")
            dialog.setMinimumWidth(600)
            
            layout = QVBoxLayout()
            
            # Creación de tabla
            table = QTableWidget(0, 3)
            table.setHorizontalHeaderLabels(["Enlace", "Permisos", "Expiración"])
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            
            # Llenado de tabla
            for share in all_public_shares:
                row = table.rowCount()
                table.insertRow(row)
                
                url = share.get('url', '')
                permissions = 'Lectura' if share.get('permissions') == 1 else 'Lectura/Escritura'
                expiration = share.get('expiration', 'No expira')
                
                table.setItem(row, 0, QTableWidgetItem(url))
                table.setItem(row, 1, QTableWidgetItem(permissions))
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
            self.core.popup(error_msg)
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
                self.core.popup(error_msg)
                return []
            
            shares = response.json().get('ocs', {}).get('data', [])
            public_shares = []
            for share in shares:
                share_type = str(share.get('share_type', ''))
                permissions = str(share.get('permissions', ''))
                
                if share_type == '3' and permissions in ['1', '17']:
                    public_shares.append({
                        'url': share.get('url', ''),
                        'permissions': permissions,
                        'expiration': share.get('expiration', 'No expira'),
                        'id': share.get('id', '')
                    })
            
            return public_shares
            
        except Exception as e:
            error_msg = f"Error al obtener shares:\n{str(e)}"
            self.core.popup(error_msg)
            self.core.writeErrorLog("Error getting public shares", str(e))
            return []

    def _copy_from_table(self, table):
        #Copia el enlace seleccionado con verificación
        selected = table.selectedItems()
        
        if not selected:
            self.core.popup("Error: No hay nada seleccionado")
            return
        
        url = selected[0].text()
        if not url:
            self.core.popup("Error: El enlace está vacío")
            return
        
        self.core.copyToClipboard(url, file=False)
        self.core.popup(f"Enlace copiado:\n{url}")

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

    def save_nextcloud_credentials(self, username, password, url):
        if not all([username, password, url]):
            self.core.popup("Error: The url, username and password cannot be empty")
            return
        
        try:
            # Determinar la ruta del archivo JSON
            config_dir = os.path.dirname(os.path.abspath(__file__))
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "nextcloud_credentials.json")
            
            # Definir la estructura de datos a guardar
            credentials = {
                "nextcloud_username": username,
                "nextcloud_password": password,
                "nextcloud_url": url
            }

            # Guardar en archivo JSON
            with open(config_file, 'w') as f:
                json.dump(credentials, f, indent=4)
            print("Credentials saved successfully!")
            
            # Actualizar la configuración actual
            self.nextcloud_user = username
            self.nextcloud_password = password
            self.nextcloud_url = url
            
            self.core.popup("Credentials saved successfully in JSON file!")
        except Exception as e:
            self.core.popup(f"Error saving credentials: {str(e)}")

    def load_nextcloud_credentials(self):
        #Función para cargar las credenciales desde el archivo json"
        try:
            config_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(config_dir, "nextcloud_credentials.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    credentials = json.load(f)
                    return (
                        credentials.get("nextcloud_username", ""),
                        credentials.get("nextcloud_password", ""),
                        credentials.get("nextcloud_url", "")
                    )
        except Exception as e:
            print(f"Error loading credentials: {str(e)}")
        
        return ("", "", "")

    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True
    


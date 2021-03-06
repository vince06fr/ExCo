
# -*- coding: utf-8 -*-

"""
Copyright (c) 2013-2017 Matic Kukovec. 
Released under the GNU GPL3 license.

For more information check the 'LICENSE.txt' file.
For complete license information of the dependencies, check the 'additional_licenses' directory.
"""

##  FILE DESCRIPTION:
##      Various helper PyQt forms used by the forms module

import os
import os.path
import collections
import traceback
import ast
import inspect
import math
import functools
import difflib
import re
import time
import settings
import functions
import forms
import data
import components
import themes



"""
-------------------------------------------------
Session manipulation object
-------------------------------------------------
"""
class SessionGuiManipulator(data.QTreeView):
    """
    GUI object for easier user editing of sessions
    """
    class SessionItem(data.PyQt.QtGui.QStandardItem):
        """QStandarItem with overridden methods"""
        #The session that the standard item will store
        my_parent   = None
        name        = None
        type        = None
        session     = None
    
    #Class constants
    class ItemType:
        SESSION         = 0
        GROUP           = 1
        EMPTY_SESSION   = 2
        EMPTY_GROUP     = 3
    
    #Class variables
    parent                  = None
    main_form               = None
    settings_manipulator    = None
    current_icon            = None
    icon_manipulator        = None
    name                    = ""
    savable                 = data.CanSave.NO
    last_clicked_session    = None
    tree_model              = None
    session_nodes           = None
    refresh_lock            = False
    edit_flag               = False
    last_created_item       = None
    session_toolbar         = None
    #Icons
    node_icon_group         = None
    node_icon_session       = None
    icon_session_add        = None
    icon_session_remove     = None
    icon_session_overwrite  = None
    icon_group_add          = None
    icon_session_edit       = None
    
    
    def clean_up(self):
        # Disconnect signals
        self.doubleClicked.disconnect()
        # Clean up main references
        self.parent = None
        self.main_form = None
        self.settings_manipulator = None
        self.icon_manipulator = None
        self.session_toolbar.setParent(None)
        self.session_toolbar.deleteLater()
        self.session_toolbar = None
        # Clean up self
        self.setParent(None)
        self.deleteLater()
    
    def __init__(self, settings_manipulator, parent, main_form):
        """Initialization"""
        #Initialize the superclass
        super().__init__(parent)
        # Initialize components
        self.icon_manipulator = components.IconManipulator()
        #Store the reference to the parent BasicWidget from the "forms" module
        self.parent = parent
        #Store the reference to the MainWindow form from the "forms" module
        self.main_form = main_form
        #Store the reference to the active SettingsManipulator
        self.settings_manipulator = settings_manipulator
        #Set the icon
        self.current_icon = functions.create_icon("tango_icons/sessions.png")
        #Store name of self
        self.name = "Session editing tree display"
        #Enable node expansion on double click
        self.setExpandsOnDoubleClick(True)
        #Set the node icons
        self.node_icon_group        = functions.create_icon("tango_icons/folder.png")
        self.node_icon_session      = functions.create_icon("tango_icons/sessions.png")
        self.icon_session_add       = functions.create_icon("tango_icons/session-add.png")
        self.icon_session_remove    = functions.create_icon("tango_icons/session-remove.png")
        self.icon_session_overwrite = functions.create_icon("tango_icons/session-overwrite.png")
        self.icon_group_add         = functions.create_icon("tango_icons/folder-add.png")
        self.icon_session_edit      = functions.create_icon("tango_icons/session-edit.png")
        #Connect the signals
        self.doubleClicked.connect(self._item_double_clicked)
    
    def clean_model(self):
        return
        if self.model() != None:
            self.model().setParent(None)
            self.setModel(None)
    
    def mousePressEvent(self, event):
        """Function connected to the clicked signal of the tree display"""
        super().mousePressEvent(event)
        #Set the focus
        self.setFocus()
        #Set the last focused widget to the parent basic widget
        self.main_form.last_focused_widget = self.parent
        data.print_log("Stored \"{:s}\" as last focused widget".format(self.parent.name))
        #Set Save/SaveAs buttons in the menubar
        self.parent._set_save_status()
        # Reset the click&drag context menu action
        components.ActionFilter.clear_action()
    
    def setFocus(self):
        """Overridden focus event"""
        #Execute the supeclass focus function
        super().setFocus()
        #Check indication
        self.main_form.view.indication_check()
    
    def _item_double_clicked(self, model_index):
        """Callback connected to the treeview's 'clicked' signal"""
        session_item = self.tree_model.itemFromIndex(model_index)
        if session_item.type == self.ItemType.SESSION:
            #Open the session
            session = session_item.session
            #This is a call to the MainWindow class in the forms module
            self.main_form.sessions.restore(session.name, session.group)
        elif session_item.type == self.ItemType.GROUP:
            pass
    
    def _item_changed(self, item):
        """Callback connected to the displays QStandardItemModel 'itemChanged' signal"""
        #Get the clicked item
        changed_item = item
        #Check for editing
        if self.edit_flag == True:
            if changed_item.type == self.ItemType.SESSION:
                #Item is a session
                old_item_name = item.session.name
                new_item_name = self.indexWidget(item.index()).text()
                #Rename all of the sessions with the group name and store them in a new list
                new_session_list = []
                for session in self.settings_manipulator.stored_sessions:
                    if session.name == old_item_name and session.group == item.session.group:
                        session.name = new_item_name
                    new_session_list.append(session)
                #Replace the old list with the new
                self.settings_manipulator.stored_sessions = new_session_list
                #Save the the new session list by saving the settings
                self.settings_manipulator.save_settings(
                    self.settings_manipulator.main_window_side, 
                    data.theme
                )
                #Update the main forms session menu
                self.main_form.sessions.update_menu()
                #Display successful group deletion
                group_name = item.session.group
                if group_name == None:
                    group_name = ""
                else:
                    group_name += " / "
                self.main_form.display.repl_display_message(
                    "Session '{:s}{:s}' was renamed to '{:s}{:s}'!".format(
                       group_name, 
                       old_item_name,  
                       group_name, 
                       new_item_name 
                    ), 
                    message_type=data.MessageType.SUCCESS
                )
                #Refresh the session tree
                self.refresh_display()
                #Refresh the session tree
                self.refresh_display()
            elif changed_item.type == self.ItemType.GROUP:
                #Item is a group
                old_group_name = item.name
                new_group_name = self.indexWidget(item.index()).text()
                #Rename all of the session with the group name and store them in a new list
                new_session_list = []
                for session in self.settings_manipulator.stored_sessions:
                    if session.group == old_group_name:
                        session.group = new_group_name
                    new_session_list.append(session)
                #Replace the old list with the new
                self.settings_manipulator.stored_sessions = new_session_list
                #Save the the new session list by saving the settings
                self.settings_manipulator.save_settings(
                    self.settings_manipulator.main_window_side, 
                    data.theme
                )
                #Update the main forms session menu
                self.main_form.sessions.update_menu()
                #Display successful group deletion
                self.main_form.display.repl_display_message(
                    "Group '{:s}' was renamed to '{:s}'!".format(
                                                                old_group_name, 
                                                                new_group_name
                                                            ), 
                    message_type=data.MessageType.SUCCESS
                )
                #Refresh the session tree
                self.refresh_display()
        else:
            if changed_item.type == self.ItemType.SESSION:
                #Item is a session
    #            session = changed_item.session
                pass
            elif changed_item.type == self.ItemType.GROUP:
                #Item is a group
    #            group_name = changed_item.name
                pass
            elif changed_item.type == self.ItemType.EMPTY_SESSION:
                #Store the session
                session = changed_item.session
                #Adjust the name to the new one, by getting the QLineEdit at the model index
                session.name = self.indexWidget(item.index()).text()
                #This is a call to the MainWindow class in the forms module
                self.main_form.sessions.add(session.name, session.group)
                #Refresh the session tree
                self.refresh_display()
                self.last_created_item = self.ItemType.EMPTY_SESSION
            elif changed_item.type == self.ItemType.EMPTY_GROUP:
                #Adjust the name to the new one, by getting the QLineEdit at the model index
                group_name = self.indexWidget(item.index()).text()
                #When the item's name is change it refires the itemChanged signal,
                #so a check of one of the properties is necessary to not repeat the operation
                if item.name == "":
                    item.name = group_name
                    item.setEditable(False)
                    #Display the warning
                    message = "An empty group was created.\n"
                    message += "A session must be added to it or the empty group will \n"
                    message += "be deleted on the next refresh!"
                    self.main_form.display.repl_display_message(
                        message, 
                        message_type=data.MessageType.WARNING
                    )
                    #Set the refresh lock, so it won't delete the empty group node
                    self.refresh_lock = True
                    self.last_created_item = self.ItemType.EMPTY_GROUP
    
    def _item_editing_closed(self, widget):
        """Signal that fires when editing was canceled/ended in an empty session or empty group"""
        if (self.refresh_lock == True and 
            self.last_created_item == self.ItemType.EMPTY_GROUP):
            return
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh the displayed session while keeping the expanded groups"""
        #Reset the all locks/flags
        self.refresh_lock   = False
        self.edit_flag      = False
        #Store which groups are expanded
        expanded_groups = []
        for group in self.groups.items():
            if self.isExpanded(group[1].index()):
                expanded_groups.append(group[0])
        #Remove the empty node by refreshing the session tree
        self.show_sessions()
        #Expand the groups that were expanded before
        for exp_group in expanded_groups:
            for group in self.groups.items():
                if group[0] == exp_group:
                    self.expand(group[1].index())
    
    def add_empty_group(self):
        #Check for various flags
        if self.edit_flag == True:
            return
        #Check if an empty group is already present
        for session_node in self.session_nodes:
            if session_node.type == self.ItemType.EMPTY_GROUP:
                return
        empty_group_node = self.SessionItem("")
        empty_group_node.parent    = self
        empty_group_node.name      = ""
        empty_group_node.session   = None
        empty_group_node.type      = self.ItemType.EMPTY_GROUP
        empty_group_node.setEditable(True)
        empty_group_node.setIcon(self.node_icon_group)
        self.tree_model.appendRow(empty_group_node)
        #Start editing the new empty group
        self.session_nodes.append(empty_group_node)
        self.edit(empty_group_node.index())
        #Add the session signal when editing is canceled
        delegate = self.itemDelegate(empty_group_node.index())
        delegate.closeEditor.connect(self._item_editing_closed)
        #Store last created node type
        self.last_created_item = self.ItemType.EMPTY_GROUP
    
    def add_empty_session(self):
        #Check for various flags
        if self.edit_flag == True:
            return
        #Check if an empty session is already present
        for session_node in self.session_nodes:
            if session_node.type == self.ItemType.EMPTY_SESSION:
                return
        #Check where the session will be added
        attachment_item = self.tree_model
        has_group = False
        if self.selectedIndexes() != []:
            selected_item = self.tree_model.itemFromIndex(self.selectedIndexes()[0])
            if selected_item.type == self.ItemType.SESSION:
                if selected_item.session.group != None:
                    attachment_item = selected_item.parent()
                    self.expand(attachment_item.index())
                    has_group = True
            elif (selected_item.type == self.ItemType.GROUP or 
                  selected_item.type == self.ItemType.EMPTY_GROUP):
                has_group = True
                attachment_item = selected_item
                self.expand(attachment_item.index())
        #Initialize the session
        empty_session = settings.Session("")
        if has_group == True:
            empty_session.group = attachment_item.name
        empty_session_node = self.SessionItem("")
        empty_session_node.parent    = self
        empty_session_node.name      = ""
        empty_session_node.session   = empty_session
        empty_session_node.type      = self.ItemType.EMPTY_SESSION
        empty_session_node.setEditable(True)
        empty_session_node.setIcon(self.node_icon_session)
        attachment_item.appendRow(empty_session_node)
        #Start editing the new empty session
        self.session_nodes.append(empty_session_node)
        self.edit(empty_session_node.index())
        #Add the session signal when editing is canceled
        delegate = self.itemDelegate(empty_session_node.index())
        delegate.closeEditor.connect(self._item_editing_closed)
        #Store last created node type
        self.last_created_item = self.ItemType.EMPTY_SESSION
    
    def remove_session(self):
        #Check for various flags
        if self.edit_flag == True:
            return
        #Check if an item is selected
        if self.selectedIndexes() == []:
            return
        selected_item = self.tree_model.itemFromIndex(self.selectedIndexes()[0])
        #Check the selected item type
        if selected_item.type == self.ItemType.GROUP:
            remove_group_name = selected_item.name
            message =  "Are you sure you want to delete group:\n"
            message += "'{:s}' ?".format(remove_group_name)
            reply = YesNoDialog(message).exec_()
            if reply == data.QMessageBox.No:
                return
            #Delete all of the session with the group name
            for session in self.settings_manipulator.stored_sessions:
                if session.group == remove_group_name:
                    self.main_form.sessions.remove(session.name, session.group)
            #Display successful group deletion
            self.main_form.display.repl_display_message(
                "Group '{:s}' was deleted!".format(remove_group_name), 
                message_type=data.MessageType.SUCCESS
            )
            #Refresh the tree
            self.refresh_display()
        elif selected_item.type == self.ItemType.SESSION:
            remove_session = selected_item.session
            group_name = remove_session.group
            if group_name == None:
                group_name = ""
            else:
                group_name += " / "
            message =  "Are you sure you want to delete session:\n"
            message += "'{:s}{:s}' ?".format(group_name, remove_session.name)
            reply = YesNoDialog.warning(message)
            if reply == data.QMessageBox.No:
                return
            #Delete the session
            #Delete all of the session with the group name
            for session in self.settings_manipulator.stored_sessions:
                if (session.name == remove_session.name and
                    session.group == remove_session.group):
                    self.main_form.sessions.remove(session.name, session.group)
                    break
            #Refresh the tree
            self.refresh_display()
        elif selected_item.type == self.ItemType.EMPTY_SESSION:
            #Display successful group deletion
            self.main_form.display.repl_display_message(
                "Empty session was deleted!", 
                message_type=data.MessageType.SUCCESS
            )
            #Refresh the tree
            self.refresh_display()
        elif selected_item.type == self.ItemType.EMPTY_GROUP:
            #Display successful group deletion
            self.main_form.display.repl_display_message(
                "Empty group was deleted!", 
                message_type=data.MessageType.SUCCESS
            )
            #Refresh the tree
            self.refresh_display()
    
    def overwrite_session(self):
        """Overwrite the selected session"""
        #Check for various flags
        if self.edit_flag == True:
            return
        #Check if a session is selected
        if self.selectedIndexes() == []:
            return
        selected_item = self.tree_model.itemFromIndex(self.selectedIndexes()[0])
        #Check the selected item type
        if selected_item.type == self.ItemType.GROUP:
            #Show message that groups cannot be overwritten
            self.main_form.display.repl_display_message(
                "Groups cannot be overwritten!", 
                message_type=data.MessageType.ERROR
            )
            return
        elif selected_item.type == self.ItemType.SESSION:
            selected_session = selected_item.session
            #Adding a session that is already stored will overwrite it
            self.main_form.sessions.add(selected_session.name, selected_session.group)
            #Refresh the tree
            self.refresh_display()
    
    def edit_item(self):
        """Edit the selected session or group name"""
        if self.edit_flag == True:
            return
        #Check if an item is selected
        if self.selectedIndexes() == []:
            return
        selected_item = self.tree_model.itemFromIndex(self.selectedIndexes()[0])
        #Check the selected item type
        if selected_item.type == self.ItemType.GROUP or selected_item.type == self.ItemType.SESSION:
            selected_item.setEditable(True)
            self.edit(selected_item.index())
        #Add the session signal when editing is canceled
        delegate = self.itemDelegate(selected_item.index())
        delegate.closeEditor.connect(self._item_editing_closed)
        #Set the editing flag
        self.edit_flag = True
    
    def show_sessions(self):
        """Show the current session in a tree structure"""
        #Initialize the display
        self.tree_model = data.PyQt.QtGui.QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["SESSIONS"])
        self.header().hide()
        self.clean_model()
        self.setModel(self.tree_model)
        self.setUniformRowHeights(True)
        #Connect the tree model signals
        self.tree_model.itemChanged.connect(self._item_changed)
        font    = data.PyQt.QtGui.QFont("Courier", 10, data.PyQt.QtGui.QFont.Bold)
        #First add all of the groups, if any
        self.groups = {}
        for session in self.settings_manipulator.stored_sessions:
            if session.group != None:
                if not(session.group in self.groups):
                    item_group_node = self.SessionItem(session.group)
                    item_group_node.setFont(font)
                    item_group_node.my_parent   = self
                    item_group_node.name        = session.group
                    item_group_node.session     = None
                    item_group_node.type        = self.ItemType.GROUP
                    item_group_node.setEditable(False)
                    item_group_node.setIcon(self.node_icon_group)
                    self.groups[session.group] = item_group_node
        #Add the groups to the display
        for self.group in collections.OrderedDict(sorted(self.groups.items())).items():
            self.tree_model.appendRow(self.group[1])
        #Initialize the list of session nodes
        self.session_nodes = []
        #Loop through the manipulators sessions and add them to the display
        for session in self.settings_manipulator.stored_sessions:
            item_session_node = self.SessionItem(session.name)
            item_session_node.my_parent = self
            item_session_node.name      = session.name
            item_session_node.session   = session
            item_session_node.type      = self.ItemType.SESSION
            item_session_node.setEditable(False)
            item_session_node.setIcon(self.node_icon_session)
            #Check if the item is in a group
            if session.group != None:
                self.groups[session.group].appendRow(item_session_node)
            else:
                self.tree_model.appendRow(item_session_node)
            #Append the session to the stored node list
            self.session_nodes.append(item_session_node)
    
    def show_session_buttons(self, parent):
        """
        Create and display buttons for manipulating sessions
        on the parent basic widget
        """
        # Clean up the toolbar if it exists
        if self.session_toolbar != None:
            self.session_toolbar.setParent(None)
            self.session_toolbar.deleteLater()
            self.session_toolbar = None
        #Create the find toolbar and buttons
        self.session_toolbar = data.QToolBar(parent)
        self.session_toolbar.setIconSize(data.PyQt.QtCore.QSize(16,16))
        session_add_action = data.QAction(
            self.icon_session_add, 
            "session_add",
            parent
        )
        session_add_action.setToolTip(
            "Add a new session"
        )
        session_add_action.triggered.connect(self.add_empty_session)
        session_remove_action = data.QAction(
            self.icon_session_remove, 
            "session_remove",
            parent
        )
        session_remove_action.setToolTip(
            "Remove the selected session"
        )
        session_remove_action.triggered.connect(self.remove_session)
        session_overwrite_action = data.QAction(
            self.icon_session_overwrite, 
            "session_overwrite",
            parent
        )
        session_overwrite_action.setToolTip(
            "Overwrite the selected session"
        )
        session_overwrite_action.triggered.connect(self.overwrite_session)
        session_add_group_action = data.QAction(
            self.icon_group_add, 
            "session_add_group",
            parent
        )
        session_add_group_action.setToolTip(
            "Add a new group"
        )
        session_add_group_action.triggered.connect(self.add_empty_group)
        session_edit_action = data.QAction(
            self.icon_session_edit, 
            "session_edit",
            parent
        )
        session_edit_action.setToolTip(
            "Edit the selected item"
        )
        session_edit_action.triggered.connect(self.edit_item)
        self.session_toolbar.addAction(session_edit_action)
        self.session_toolbar.addAction(session_overwrite_action)
        self.session_toolbar.addAction(session_add_group_action)
        self.session_toolbar.addAction(session_add_action)
        self.session_toolbar.addAction(session_remove_action)
        self.session_toolbar.show()
        #Set the corner widget of the parent
        parent.setCornerWidget(self.session_toolbar)



"""
----------------------------------------------------------------------------
Object for displaying various results in a tree structure
----------------------------------------------------------------------------
"""
class TreeDisplay(data.QTreeView):
    #Class custom objects/types
    class Directory():
        """
        Object for holding directory/file information when building directory trees
        """
        item        = None
        directories = None
        files       = None
        
        def __init__(self, input_item):
            """Initialization"""
            self.item = input_item
            self.directories = {}
            self.files = {}
        
        def add_directory(self, dir_name, dir_item):
            #Create a new instance of Directory class using the __class__ dunder method
            new_directory = self.__class__(dir_item)
            #Add the new directory to the dictionary
            self.directories[dir_name] = new_directory
            #Add the new directory item to the parent(self)
            self.item.appendRow(dir_item)
            #Return the directory object reference
            return new_directory
        
        def add_file(self, file_name, file_item):
            self.files[file_name] = file_item
            #Add the new file item to the parent(self)
            self.item.appendRow(file_item)
    
    #Class variables
    parent                  = None
    main_form               = None
    name                    = ""
    savable                 = data.CanSave.NO
    current_icon            = None
    icon_manipulator        = None
    tree_display_type       = None
    tree_menu               = None
    bound_tab               = None
    #Attributes specific to the display data
    bound_node_tab          = None
    #Node icons
    node_icon_import        = None
    node_icon_type          = None
    node_icon_const         = None
    node_icon_function      = None
    node_icon_procedure     = None
    node_icon_converter     = None
    node_icon_iterator      = None
    node_icon_class         = None
    node_icon_method        = None
    node_icon_property      = None
    node_icon_macro         = None
    node_icon_template      = None
    node_icon_variable      = None
    node_icon_namespace     = None
    node_icon_nothing       = None
    node_pragma             = None
    folder_icon             = None
    goto_icon               = None
    python_icon             = None
    nim_icon                = None
    c_icon                  = None
    
    
    def clean_up(self):
        # Clean up the tree model
        self.clean_model()
        # Disconnect signals
        self.doubleClicked.disconnect()
        self.expanded.disconnect()
        # Clean up main references
        self.main_form.node_tree_tab = None
        self.parent = None
        self.main_form = None
        self.icon_manipulator = None
        self.bound_tab = None
        if self.tree_menu != None:
            self.tree_menu.setParent(None)
            self.tree_menu = None
        # Clean up self
        self.setParent(None)
        self.deleteLater()
    
    def parent_destroyed(self, event):
        # Connect the bound tab 'destroy' signal to this function
        # for automatic closing of this tree widget
        self.parent.close_tab(self)
    
    def __init__(self, parent=None, main_form=None):
        """Initialization"""
        # Initialize the superclass
        super().__init__(parent)
        # Initialize components
        self.icon_manipulator = components.IconManipulator()
        # Store the reference to the parent
        self.parent = parent
        # Store the reference to the main form
        self.main_form = main_form
        # Store name of self
        self.name = "Tree display"
        # Disable node expansion on double click
        self.setExpandsOnDoubleClick(False)
        # Connect the click and doubleclick signal
        self.doubleClicked.connect(self._item_double_click)
#        self.clicked.connect(self._item_click)
        # Connect the doubleclick signal
        self.expanded.connect(self._check_contents)
        # Initialize the icons
        # Node icons
        self.node_icon_import   = functions.create_icon("various/node_module.png")
        self.node_icon_type     = functions.create_icon("various/node_type.png")
        self.node_icon_variable = functions.create_icon("various/node_variable.png")
        self.node_icon_const    = functions.create_icon("various/node_const.png")
        self.node_icon_function = functions.create_icon("various/node_function.png")
        self.node_icon_procedure= functions.create_icon("various/node_procedure.png")
        self.node_icon_converter= functions.create_icon("various/node_converter.png")
        self.node_icon_iterator = functions.create_icon("various/node_iterator.png")
        self.node_icon_class    = functions.create_icon("various/node_class.png")
        self.node_icon_method   = functions.create_icon("various/node_method.png")
        self.node_icon_macro    = functions.create_icon("various/node_macro.png")
        self.node_icon_template = functions.create_icon("various/node_template.png")
        self.node_icon_namespace= functions.create_icon("various/node_namespace.png")
        self.node_icon_pragma   = functions.create_icon("various/node_pragma.png")
        self.node_icon_nothing  = functions.create_icon("tango_icons/dialog-warning.png")
        self.python_icon        = functions.create_icon("language_icons/logo_python.png")
        self.nim_icon           = functions.create_icon("language_icons/logo_nim.png")
        self.c_icon             = functions.create_icon("language_icons/logo_c.png")
        # File searching icons
        self.file_icon      = functions.create_icon("tango_icons/file.png")
        self.folder_icon    = functions.create_icon("tango_icons/folder.png")
        self.goto_icon      = functions.create_icon('tango_icons/edit-goto.png')
        
        # Set the icon size for every node
        self.update_icon_size()
        
            
    def update_icon_size(self):
        self.setIconSize(
            data.PyQt.QtCore.QSize(
                data.tree_display_icon_size, data.tree_display_icon_size
            )
        )
    
    def setFocus(self):
        """Overridden focus event"""
        # Execute the supeclass focus function
        super().setFocus()
        # Check indication
        self.main_form.view.indication_check()
    
    def mousePressEvent(self, event):
        """Function connected to the clicked signal of the tree display"""
        super().mousePressEvent(event)
        # Set the focus
        self.setFocus()
        # Set the last focused widget to the parent basic widget
        self.main_form.last_focused_widget = self.parent
        data.print_log("Stored \"{:s}\" as last focused widget".format(self.parent.name))
        # Set Save/SaveAs buttons in the menubar
        self.parent._set_save_status()
        # Get the index of the clicked item and execute the item's procedure
        if event.button() == data.PyQt.QtCore.Qt.RightButton:
            index = self.indexAt(event.pos())
            self._item_click(index)
        # Reset the click&drag context menu action
        components.ActionFilter.clear_action()
    
    def _item_click(self, model_index):
        if self.tree_display_type == data.TreeDisplayType.FILES:
            item = self.model().itemFromIndex(model_index)
            if (hasattr(item, "is_dir") == True or 
                hasattr(item, "is_base") == True):
                def update_cwd():
                    self.main_form.set_cwd(item.full_name)
                cursor = data.PyQt.QtGui.QCursor.pos()
                
                if self.tree_menu != None:
                    self.tree_menu.setParent(None)
                    self.tree_menu = None

                self.tree_menu = data.QMenu()
                action_update_cwd = data.QAction("Update CWD", self.tree_menu)
                action_update_cwd.triggered.connect(update_cwd)
                icon = functions.create_icon('tango_icons/update-cwd.png')
                action_update_cwd.setIcon(icon)
                self.tree_menu.addAction(action_update_cwd)
                if hasattr(item, "is_base") == True:
                    def update_to_parent():
                        parent_directory = os.path.abspath(
                            os.path.join(item.full_name, os.pardir)
                        )
                        self.main_form.set_cwd(parent_directory)
                    action_update_to_parent = data.QAction(
                        "Update CWD to parent", self.tree_menu
                    )
                    action_update_to_parent.triggered.connect(update_to_parent)
                    icon = functions.create_icon('tango_icons/update-cwd.png')
                    action_update_to_parent.setIcon(icon)
                    self.tree_menu.addAction(action_update_to_parent)
                    self.tree_menu.addSeparator()
                    def one_dir_up():
                        parent_directory = os.path.abspath(
                            os.path.join(item.full_name, os.pardir)
                        )
                        self.main_form.display.show_directory_tree(
                            parent_directory
                        )
                    action_one_dir_up = data.QAction(
                        "One directory up ..", self.tree_menu
                    )
                    action_one_dir_up.triggered.connect(one_dir_up)
                    icon = functions.create_icon('tango_icons/one-dir-up.png')
                    action_one_dir_up.setIcon(icon)
                    self.tree_menu.addAction(action_one_dir_up)
                self.tree_menu.popup(cursor)
            elif hasattr(item, "full_name") == True:
                def open_file():
                    self.main_form.open_file(item.full_name)
                cursor = data.PyQt.QtGui.QCursor.pos()
                
                if self.tree_menu != None:
                    self.tree_menu.setParent(None)
                    self.tree_menu = None
                
                self.tree_menu = data.QMenu()
                action_open_file = data.QAction("Open", self.tree_menu)
                action_open_file.triggered.connect(open_file)
                icon = functions.create_icon('tango_icons/document-open.png')
                action_open_file.setIcon(icon)
                self.tree_menu.addAction(action_open_file)
                self.tree_menu.addSeparator()
                def update_to_parent():
                    directory = os.path.dirname(item.full_name)
                    self.main_form.set_cwd(directory)
                action_update_to_parent = data.QAction(
                    "Update CWD", self.tree_menu
                )
                action_update_to_parent.triggered.connect(update_to_parent)
                icon = functions.create_icon('tango_icons/update-cwd.png')
                action_update_to_parent.setIcon(icon)
                self.tree_menu.addAction(action_update_to_parent)
                self.tree_menu.popup(cursor)
        
        elif self.tree_display_type == data.TreeDisplayType.NODES:
            def goto_item():
                #Parse the node
                self._node_item_parse(item)
            
            def open_document():
                #Focus the bound tab in its parent window
                self.bound_tab.parent.setCurrentWidget(self.bound_tab)
            
            item = self.model().itemFromIndex(model_index)
            item_text = item.text()
            cursor = data.PyQt.QtGui.QCursor.pos()
            
            if self.tree_menu != None:
                self.tree_menu.setParent(None)
                self.tree_menu = None
            
            self.tree_menu = data.QMenu()
            
            if (hasattr(item, "line_number") == True or "line:" in item_text):
                action_goto_line = data.QAction("Goto node item", self.tree_menu)
                action_goto_line.triggered.connect(goto_item)
                icon = functions.create_icon('tango_icons/edit-goto.png')
                action_goto_line.setIcon(icon)
                self.tree_menu.addAction(action_goto_line)
            elif "DOCUMENT" in item_text:
                action_open = data.QAction("Focus document", self.tree_menu)
                action_open.triggered.connect(open_document)
                icon = functions.create_icon('tango_icons/document-open.png')
                action_open.setIcon(icon)
                self.tree_menu.addAction(action_open)

            self.tree_menu.popup(cursor)
    
    def _item_double_click(self, model_index):
        """Function connected to the doubleClicked signal of the tree display"""
        #Use the item text according to the tree display type
        if self.tree_display_type == data.TreeDisplayType.NODES:
            #Get the text of the double clicked item
            item = self.model().itemFromIndex(model_index)
            self._node_item_parse(item)
        elif self.tree_display_type == data.TreeDisplayType.FILES:
            #Get the double clicked item
            item = self.model().itemFromIndex(model_index)
            #Test if the item has the 'full_name' attribute
            if hasattr(item, "is_dir") == True:
                #Expand/collapse the directory node
                if self.isExpanded(item.index()) == True:
                    self.collapse(item.index())
                else:
                    self.expand(item.index())
                return
            elif hasattr(item, "full_name") == True:
                #Open the file
                self.main_form.open_file(file=item.full_name)
        elif self.tree_display_type == data.TreeDisplayType.FILES_WITH_LINES:
            #Get the double clicked item
            item = self.model().itemFromIndex(model_index)
            #Test if the item has the 'full_name' attribute
            if hasattr(item, "full_name") == False:
                return
            #Open the file
            self.main_form.open_file(file=item.full_name)
            #Check if a line item was clicked
            if hasattr(item, "line_number") == True:
                #Goto the stored line number
                document = self.main_form.main_window.currentWidget()
                document.goto_line(item.line_number)
    
    def _node_item_parse(self, item):
        # Check if the bound tab has been cleaned up and has no parent
        if self.bound_tab == None or self.bound_tab.parent == None:
            self.main_form.display.repl_display_message(
                "The bound tab has been closed! Reload the tree display.", 
                message_type=data.MessageType.ERROR
            )
            return
        # Check the item text
        item_text = item.text()
        if hasattr(item, "line_number") == True:
            # Goto the stored line number
            self.bound_tab.parent.setCurrentWidget(self.bound_tab)
            self.bound_tab.goto_line(item.line_number)
        elif "line:" in item_text:
            # Parse the line number out of the item text
            line = item_text.split()[-1]
            start_index = line.index(":") + 1
            end_index   = -1
            line_number = int(line[start_index:end_index])
            # Focus the bound tab in its parent window
            self.bound_tab.parent.setCurrentWidget(self.bound_tab)
            # Go to the item line number
            self.bound_tab.goto_line(line_number)
        elif "DOCUMENT" in item_text:
            # Focus the bound tab in its parent window
            self.bound_tab.parent.setCurrentWidget(self.bound_tab)
    
    def _check_contents(self):
        #Update the horizontal scrollbar width
        self.resize_horizontal_scrollbar()
    
    def set_font_size(self, size_in_points):
        """Set the font size for the tree display items"""
        #Initialize the font with the new size
        new_font = data.PyQt.QtGui.QFont('Courier', size_in_points)
        #Set the new font
        self.setFont(new_font)
    
    def set_display_type(self, tree_type):
        """Set the tree display type attribute"""
        self.tree_display_type = tree_type
    
    def resize_horizontal_scrollbar(self):
        """
        Resize the header so the horizontal scrollbar will have the correct width
        """
        for i in range(self.model().rowCount()):
            self.resizeColumnToContents(i)
    
    def display_python_nodes_in_list(self, 
                                     custom_editor,
                                     import_nodes, 
                                     class_nodes,
                                     function_nodes,
                                     global_vars, 
                                     parse_error=False):
        """Display the input python data in the tree display"""
        #Store the custom editor tab that for quicker navigation
        self.bound_tab = custom_editor
        #Set the tree display type to NODE
        self.set_display_type(data.TreeDisplayType.NODES)
        #Define the document name, type
        document_name       = os.path.basename(custom_editor.save_name)
        document_name_text  = "DOCUMENT: {:s}".format(document_name)
        document_type_text  = "TYPE: {:s}".format(custom_editor.current_file_type)
        #Define the display structure texts
        import_text         = "IMPORTS:"
        class_text          = "CLASS/METHOD TREE:"
        function_text       = "FUNCTIONS:"
        #Initialize the tree display to Python file type
        self.setSelectionBehavior(data.QAbstractItemView.SelectRows)
        tree_model = data.PyQt.QtGui.QStandardItemModel()
        tree_model.setHorizontalHeaderLabels([document_name])
        self.clean_model()
        self.setModel(tree_model)
        self.setUniformRowHeights(True)
        self.set_font_size(data.tree_display_font_size)
        #Add the file attributes to the tree display
        description_brush = data.PyQt.QtGui.QBrush(
            data.PyQt.QtGui.QColor(data.theme.Font.Python.Keyword[1])
        )
        description_font = data.PyQt.QtGui.QFont(
            "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
        )
        item_document_name  = data.PyQt.QtGui.QStandardItem(document_name_text)
        item_document_name.setEditable(False)
        item_document_name.setForeground(description_brush)
        item_document_name.setFont(description_font)
        item_document_type = data.PyQt.QtGui.QStandardItem(document_type_text)
        item_document_type.setEditable(False)
        item_document_type.setForeground(description_brush)
        item_document_type.setFont(description_font)
        item_document_type.setIcon(self.python_icon)
        tree_model.appendRow(item_document_name)
        tree_model.appendRow(item_document_type)
        #Set the label properties
        label_brush = data.PyQt.QtGui.QBrush(
            data.PyQt.QtGui.QColor(data.theme.Font.Python.SingleQuotedString[1])
        )
        label_font  = data.PyQt.QtGui.QFont(
            "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
        )
        #Check if there was a parsing error
        if parse_error != False:
            error_brush = data.PyQt.QtGui.QBrush(data.PyQt.QtGui.QColor(180, 0, 0))
            error_font  = data.PyQt.QtGui.QFont(
                "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
            )
            item_error = data.PyQt.QtGui.QStandardItem("ERROR PARSING FILE!")
            item_error.setEditable(False)
            item_error.setForeground(error_brush)
            item_error.setFont(error_font)
            item_error.setIcon(self.node_icon_nothing)
            tree_model.appendRow(item_error)
            #Show the error message
            error_font = data.PyQt.QtGui.QFont("Courier", data.tree_display_font_size)
            item_error_msg = data.PyQt.QtGui.QStandardItem(str(parse_error))
            item_error_msg.setEditable(False)
            item_error_msg.setForeground(error_brush)
            item_error_msg.setFont(error_font)
            line_number = int(re.search(r"line (\d+)",str(parse_error)).group(1))
            item_error_msg.line_number = line_number
            tree_model.appendRow(item_error_msg)
            return
        """Imported module filtering"""
        item_imports = data.PyQt.QtGui.QStandardItem(import_text)
        item_imports.setEditable(False)
        item_imports.setForeground(label_brush)
        item_imports.setFont(label_font)
        for node in import_nodes:
            node_text = str(node[0]) + " (line:"
            node_text += str(node[1]) + ")"
            item_import_node = data.PyQt.QtGui.QStandardItem(node_text)
            item_import_node.setEditable(False)
            item_import_node.setIcon(self.node_icon_import)
            item_imports.appendRow(item_import_node)
        if import_nodes == []:
            item_no_imports = data.PyQt.QtGui.QStandardItem("No imports found")
            item_no_imports.setEditable(False)
            item_no_imports.setIcon(self.node_icon_nothing)
            item_imports.appendRow(item_no_imports)
        #Append the import node to the model
        tree_model.appendRow(item_imports)
        if import_nodes == []:
            self.expand(item_imports.index())
        """Class nodes filtering"""
        item_classes = data.PyQt.QtGui.QStandardItem(class_text)
        item_classes.setEditable(False)
        item_classes.setForeground(label_brush)
        item_classes.setFont(label_font)
        #Check deepest nest level and store it
        max_level = 0
        for node in class_nodes:
            for child in node[1]:
                child_level = child[0] + 1
                if child_level > max_level:
                    max_level = child_level
        #Initialize the base level references to the size of the deepest nest level
        base_node_items = [None] * max_level
        base_node_type  = [None] * max_level
        #Create class nodes as tree items
        for node in class_nodes:
            #Construct the parent node
            node_text = str(node[0].name) + " (line:"
            node_text += str(node[0].lineno) + ")"
            parent_tree_node = data.PyQt.QtGui.QStandardItem(node_text)
            parent_tree_node.setEditable(False)
            parent_tree_node.setIcon(self.node_icon_class)
            #Create a list that will hold the child nodes
            child_nodes = []
            #Create base nodes
            #Create the child nodes and add them to list
            for i, child in enumerate(node[1]):
                """!! child_level IS THE INDENTATION LEVEL !!"""
                child_level     = child[0]  
                child_object    = child[1]
                child_text  = str(child_object.name) + " (line:"
                child_text  += str(child_object.lineno) + ")"
                child_tree_node = data.PyQt.QtGui.QStandardItem(child_text)
                child_tree_node.setEditable(False)
                #Save the base node, its type for adding children to it
                base_node_items[child_level]    = child_tree_node
                if isinstance(child_object, ast.ClassDef) == True:
                    base_node_type[child_level] = 0
                elif isinstance(child_object, ast.FunctionDef) == True:
                    base_node_type[child_level] = 1
                #Check if the child is a child of a child.
                if child_level != 0:
                    #Set the child icon
                    if isinstance(child_object, ast.ClassDef) == True:
                        child_tree_node.setIcon(self.node_icon_class)
                    else:
                        #Set method/function icon according to the previous base node type
                        if base_node_type[child_level-1] == 0:
                            child_tree_node.setIcon(self.node_icon_method)
                        elif base_node_type[child_level-1] == 1:
                            child_tree_node.setIcon(self.node_icon_procedure)
                    #Determine the parent node level
                    level_retraction    = 1
                    parent_level        = child_level - level_retraction
                    parent_node         = None
                    while parent_node == None and parent_level >= 0:
                        parent_node = base_node_items[parent_level]
                        level_retraction += 1
                        parent_level = child_level - level_retraction
                    #Add the child node to the parent node
                    parent_node.appendRow(child_tree_node)
                    #Sort the base node children
                    parent_node.sortChildren(0)
                else:
                    #Set the icon for the 
                    if isinstance(child_object, ast.ClassDef) == True:
                        child_tree_node.setIcon(self.node_icon_class)
                    elif isinstance(child_object, ast.FunctionDef) == True:
                        child_tree_node.setIcon(self.node_icon_method)
                    child_nodes.append(child_tree_node)
            #Append the child nodes to the parent and sort them
            for cn in child_nodes:
                parent_tree_node.appendRow(cn)
            parent_tree_node.sortChildren(0)
            #Append the parent to the model and sort them
            item_classes.appendRow(parent_tree_node)
            item_classes.sortChildren(0)
        #Append the class nodes to the model
        tree_model.appendRow(item_classes)
        #Check if there were any nodes found
        if class_nodes == []:
            item_no_classes = data.PyQt.QtGui.QStandardItem("No classes found")
            item_no_classes.setEditable(False)
            item_no_classes.setIcon(self.node_icon_nothing)
            item_classes.appendRow(item_no_classes)
        """Function nodes filtering"""
        item_functions = data.PyQt.QtGui.QStandardItem(function_text)
        item_functions.setEditable(False)
        item_functions.setForeground(label_brush)
        item_functions.setFont(label_font)
        #Create function nodes as tree items
        for func in function_nodes:
            #Set the function node text
            func_text = func.name + " (line:"
            func_text += str(func.lineno) + ")"
            #Construct the node and add it to the tree
            function_node = data.PyQt.QtGui.QStandardItem(func_text)
            function_node.setEditable(False)
            function_node.setIcon(self.node_icon_procedure)
            item_functions.appendRow(function_node)
        item_functions.sortChildren(0)
        #Check if there were any nodes found
        if function_nodes == []:
            item_no_functions = data.PyQt.QtGui.QStandardItem("No functions found")
            item_no_functions.setEditable(False)
            item_no_functions.setIcon(self.node_icon_nothing)
            item_functions.appendRow(item_no_functions)
        #Append the function nodes to the model
        tree_model.appendRow(item_functions)
        #Expand the base nodes
        self.expand(item_classes.index())
        self.expand(item_functions.index())
        #Resize the header so the horizontal scrollbar will have the correct width
        self.resize_horizontal_scrollbar()
    
    def construct_node(self, node, parent_is_class=False):
        # Construct the node text
        node_text = str(node.name) + " (line:"
        node_text += str(node.line_number) + ")"
        tree_node = data.PyQt.QtGui.QStandardItem(node_text)
        tree_node.setEditable(False)
        if node.type == "class":
            tree_node.setIcon(self.node_icon_class)
        elif node.type == "function":
            if parent_is_class == False:
                tree_node.setIcon(self.node_icon_procedure)
            else:
                tree_node.setIcon(self.node_icon_method)
        elif node.type == "global_variable":
            tree_node.setIcon(self.node_icon_variable)
        # Append the children
        node_is_class = False
        if node.type == "class":
            node_is_class = True
        for child_node in node.children:
            tree_node.appendRow(self.construct_node(child_node, node_is_class))
        # Sort the child node alphabetically
        tree_node.sortChildren(0)
        # Return the node
        return tree_node
    
    def display_python_nodes_in_tree(self, 
                                     custom_editor,
                                     python_node_tree, 
                                     parse_error=False):
        """Display the input python data in the tree display"""
        #Store the custom editor tab that for quicker navigation
        self.bound_tab = custom_editor
        #Set the tree display type to NODE
        self.set_display_type(data.TreeDisplayType.NODES)
        #Define the document name, type
        document_name       = os.path.basename(custom_editor.save_name)
        document_name_text  = "DOCUMENT: {:s}".format(document_name)
        document_type_text  = "TYPE: {:s}".format(custom_editor.current_file_type)
        #Define the display structure texts
        import_text         = "IMPORTS:"
        global_vars_text    = "GLOBALS:"
        class_text          = "CLASS/METHOD TREE:"
        function_text       = "FUNCTIONS:"
        #Initialize the tree display to Python file type
        self.setSelectionBehavior(data.QAbstractItemView.SelectRows)
        tree_model = data.PyQt.QtGui.QStandardItemModel()
        tree_model.setHorizontalHeaderLabels([document_name])
        self.clean_model()
        self.setModel(tree_model)
        self.setUniformRowHeights(True)
        self.set_font_size(data.tree_display_font_size)
        #Add the file attributes to the tree display
        description_brush = data.PyQt.QtGui.QBrush(
            data.PyQt.QtGui.QColor(data.theme.Font.Python.Keyword[1])
        )
        description_font = data.PyQt.QtGui.QFont(
            "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
        )
        item_document_name  = data.PyQt.QtGui.QStandardItem(document_name_text)
        item_document_name.setEditable(False)
        item_document_name.setForeground(description_brush)
        item_document_name.setFont(description_font)
        item_document_type  = data.PyQt.QtGui.QStandardItem(document_type_text)
        item_document_type.setEditable(False)
        item_document_type.setForeground(description_brush)
        item_document_type.setFont(description_font)
        item_document_type.setIcon(self.python_icon)
        tree_model.appendRow(item_document_name)
        tree_model.appendRow(item_document_type)
        #Set the label properties
        label_brush = data.PyQt.QtGui.QBrush(
            data.PyQt.QtGui.QColor(data.theme.Font.Python.SingleQuotedString[1])
        )
        label_font  = data.PyQt.QtGui.QFont(
            "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
        )
        #Check if there was a parsing error
        if parse_error != False:
            error_brush = data.PyQt.QtGui.QBrush(data.PyQt.QtGui.QColor(180, 0, 0))
            error_font  = data.PyQt.QtGui.QFont(
                "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
            )
            item_error = data.PyQt.QtGui.QStandardItem("ERROR PARSING FILE!")
            item_error.setEditable(False)
            item_error.setForeground(error_brush)
            item_error.setFont(error_font)
            item_error.setIcon(self.node_icon_nothing)
            tree_model.appendRow(item_error)
            #Show the error message
            error_font = data.PyQt.QtGui.QFont("Courier", data.tree_display_font_size)
            item_error_msg = data.PyQt.QtGui.QStandardItem(str(parse_error))
            item_error_msg.setEditable(False)
            item_error_msg.setForeground(error_brush)
            item_error_msg.setFont(error_font)
            try:
                line_number = int(re.search(r"line (\d+)",str(parse_error)).group(1))
                item_error_msg.line_number = line_number
            except:
                pass
            tree_model.appendRow(item_error_msg)
            return
        # Create the filtered node lists
        import_nodes = [x for x in python_node_tree if x.type == "import"]
        class_nodes = [x for x in python_node_tree if x.type == "class"]
        function_nodes = [x for x in python_node_tree if x.type == "function"]
        globals_nodes = [x for x in python_node_tree if x.type == "global_variable"]
        """Imported module filtering"""
        item_imports = data.PyQt.QtGui.QStandardItem(import_text)
        item_imports.setEditable(False)
        item_imports.setForeground(label_brush)
        item_imports.setFont(label_font)
        for node in import_nodes:
            node_text = str(node.name) + " (line:"
            node_text += str(node.line_number) + ")"
            item_import_node = data.PyQt.QtGui.QStandardItem(node_text)
            item_import_node.setEditable(False)
            item_import_node.setIcon(self.node_icon_import)
            item_imports.appendRow(item_import_node)
        if import_nodes == []:
            item_no_imports = data.PyQt.QtGui.QStandardItem("No imports found")
            item_no_imports.setEditable(False)
            item_no_imports.setIcon(self.node_icon_nothing)
            item_imports.appendRow(item_no_imports)
        #Append the import node to the model
        tree_model.appendRow(item_imports)
        if import_nodes == []:
            self.expand(item_imports.index())
        """Global variable nodes filtering"""
        item_globals = data.PyQt.QtGui.QStandardItem(global_vars_text)
        item_globals.setEditable(False)
        item_globals.setForeground(label_brush)
        item_globals.setFont(label_font)
        #Check if there were any nodes found
        if globals_nodes == []:
            item_no_globals = data.PyQt.QtGui.QStandardItem("No global variables found")
            item_no_globals.setEditable(False)
            item_no_globals.setIcon(self.node_icon_nothing)
            item_globals.appendRow(item_no_globals)
        else:
            # Create the function nodes and add them to the tree
            for node in globals_nodes:
                item_globals.appendRow(self.construct_node(node))
        #Append the function nodes to the model
        tree_model.appendRow(item_globals)
        if globals_nodes == []:
            self.expand(item_globals.index())
        """Class nodes filtering"""
        item_classes = data.PyQt.QtGui.QStandardItem(class_text)
        item_classes.setEditable(False)
        item_classes.setForeground(label_brush)
        item_classes.setFont(label_font)
        # Check if there were any nodes found
        if class_nodes == []:
            item_no_classes = data.PyQt.QtGui.QStandardItem("No classes found")
            item_no_classes.setEditable(False)
            item_no_classes.setIcon(self.node_icon_nothing)
            item_classes.appendRow(item_no_classes)
        else:
            # Create the class nodes and add them to the tree
            for node in class_nodes:
                item_classes.appendRow(self.construct_node(node, True))
        # Append the class nodes to the model
        tree_model.appendRow(item_classes)
        """Function nodes filtering"""
        item_functions = data.PyQt.QtGui.QStandardItem(function_text)
        item_functions.setEditable(False)
        item_functions.setForeground(label_brush)
        item_functions.setFont(label_font)
        #Check if there were any nodes found
        if function_nodes == []:
            item_no_functions = data.PyQt.QtGui.QStandardItem("No functions found")
            item_no_functions.setEditable(False)
            item_no_functions.setIcon(self.node_icon_nothing)
            item_functions.appendRow(item_no_functions)
        else:
            # Create the function nodes and add them to the tree
            for node in function_nodes:
                item_functions.appendRow(self.construct_node(node))
        #Append the function nodes to the model
        tree_model.appendRow(item_functions)
        """Finalization"""
        #Expand the base nodes
        self.expand(item_classes.index())
        self.expand(item_functions.index())
        #Resize the header so the horizontal scrollbar will have the correct width
        self.resize_horizontal_scrollbar()
    
    def display_c_nodes(self, custom_editor, module):
        """Display the input C data in a tree structure"""
        # Store the custom editor tab that for quicker navigation
        self.bound_tab = custom_editor
        # Set the tree display type to NODE
        self.set_display_type(data.TreeDisplayType.NODES)
        # Define the display structure texts
        function_text       = "FUNCTIONS:"
        prototype_text      = "PROTOTYPES:"
        types_text          = "TYPES:"
        variable_text       = "VARIABLES:"
        include_text        = "INCLUDES:"
        pragma_text         = "PRAGMAS:"
        define_text         = "DEFINES:"
        undefine_text       = "UN-DEFINES:"
        error_text          = "ERRORS:"
        # Set the label properties
        label_brush = data.PyQt.QtGui.QBrush(
            data.PyQt.QtGui.QColor(data.theme.Font.Python.SingleQuotedString[1])
        )
        label_font  = data.PyQt.QtGui.QFont(
            "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
        )
        # Filter the nodes
        def display_node(tree_node, c_node):
            function_list = []
            var_list = []
            prototype_list = []
            type_list = []
            include_list = []
            define_list = []
            pragma_list = []
            undef_list = []
            error_list = []
            for v in c_node.children:
                if v.type == "function":
                    function_list.append(v)
                elif v.type == "var":
                    var_list.append(v)
                elif v.type == "prototype":
                    prototype_list.append(v)
                elif (v.type == "typedef" or 
                      v.type == "struct" or 
                      v.type == "enum" or 
                      v.type == "union"):
                    type_list.append(v)
                elif v.type == "include":
                    include_list.append(v)
                elif v.type == "define":
                    define_list.append(v)
                elif v.type == "pragma":
                    pragma_list.append(v)
                elif v.type == "undef":
                    undef_list.append(v)
                elif v.type == "error":
                    error_list.append(v)
                else:
                    raise Exception("Unknown C node: {}".format(v.type))
            # Add The nodes to the tree using the parent tree node
            for i in range(9):
                if i == 0:
                    if include_list == []:
                        continue
                    item = data.PyQt.QtGui.QStandardItem(include_text)
                    icon = self.node_icon_import
                    current_list = include_list
                elif i == 1:
                    if pragma_list == []:
                        continue
                    item = data.PyQt.QtGui.QStandardItem(pragma_text)
                    icon = self.node_icon_pragma
                    current_list = pragma_list
                elif i == 2:
                    if define_list == []:
                        continue
                    item = data.PyQt.QtGui.QStandardItem(define_text)
                    icon = self.node_icon_macro
                    current_list = define_list
                elif i == 3:
                    if type_list == []:
                        continue
                    item = data.PyQt.QtGui.QStandardItem(types_text)
                    icon = self.node_icon_type
                    current_list = type_list
                elif i == 4:
                    if var_list == []:
                        continue
                    item = data.PyQt.QtGui.QStandardItem(variable_text)
                    icon = self.node_icon_variable
                    current_list = var_list
                elif i == 5:
                    if prototype_list == []:
                        continue
                    item = data.PyQt.QtGui.QStandardItem(prototype_text)
                    icon = self.node_icon_function
                    current_list = prototype_list
                elif i == 6:
                    if function_list == []:
                        continue
                    item = data.PyQt.QtGui.QStandardItem(function_text)
                    icon = self.node_icon_procedure
                    current_list = function_list
                
                elif i == 7:
                    if undef_list == []:
                        continue
                    item = data.PyQt.QtGui.QStandardItem(undefine_text)
                    icon = self.node_icon_macro
                    current_list = undef_list
                elif i == 8:
                    if error_list == []:
                        continue
                    item = data.PyQt.QtGui.QStandardItem(error_text)
                    icon = self.node_icon_macro
                    current_list = error_list
                    
                item.setEditable(False)
                item.setForeground(label_brush)
                item.setFont(label_font)
                # Create nodes as tree items
                current_list = sorted(current_list, key=lambda x: x.name)
                for n in current_list:
                    # Set the function node text
                    node_text = n.name + " (line:"
                    node_text += str(n.line_number) + ")"
                    # Construct the node and add it to the tree
                    node = data.PyQt.QtGui.QStandardItem(node_text)
                    node.setEditable(False)
                    node.setIcon(icon)
                    
                    if n.children != []:
                        display_node(node, n)
                    
                    item.appendRow(node)
                # Check if there were any nodes found
                if current_list == []:
                    item_no_nodes = data.PyQt.QtGui.QStandardItem("No items found")
                    item_no_nodes.setEditable(False)
                    item.appendRow(item_no_nodes)
                # Append the nodes to the parent node
                tree_node.appendRow(item)
        
        # Define the document name, type
        document_name       = os.path.basename(custom_editor.save_name)
        document_name_text  = "DOCUMENT: {:s}".format(document_name)
        document_type_text  = "TYPE: {:s}".format(custom_editor.current_file_type)
        # Initialize the tree display
        self.setSelectionBehavior(data.QAbstractItemView.SelectRows)
        tree_model = data.PyQt.QtGui.QStandardItemModel()
        tree_model.setHorizontalHeaderLabels([document_name])
        self.clean_model()
        self.setModel(tree_model)
        self.setUniformRowHeights(True)
        self.set_font_size(data.tree_display_font_size)
        # Add the file attributes to the tree display
        description_brush   = data.PyQt.QtGui.QBrush(
            data.PyQt.QtGui.QColor(data.theme.Font.Python.Keyword[1])
        )
        description_font    = data.PyQt.QtGui.QFont(
            "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
        )
        item_document_name  = data.PyQt.QtGui.QStandardItem(document_name_text)
        item_document_name.setEditable(False)
        item_document_name.setForeground(description_brush)
        item_document_name.setFont(description_font)
        item_document_type  = data.PyQt.QtGui.QStandardItem(document_type_text)
        item_document_type.setEditable(False)
        item_document_type.setForeground(description_brush)
        item_document_type.setFont(description_font)
        item_document_type.setIcon(self.c_icon)
        tree_model.appendRow(item_document_name)
        tree_model.appendRow(item_document_type)
        # Add the items recursively
        display_node(tree_model, module[0])
        # Resize the header so the horizontal scrollbar will have the correct width
        self.resize_horizontal_scrollbar()
    
    def display_nim_nodes(self, custom_editor, nim_nodes):
        """Display the Nim nodes in a tree structure"""
        #Store the custom editor tab that for quicker navigation
        self.bound_tab = custom_editor
        #Set the tree display type to NODE
        self.set_display_type(data.TreeDisplayType.NODES)
        #Define the document name, type
        document_name       = os.path.basename(custom_editor.save_name)
        document_name_text  = "DOCUMENT: {:s}".format(document_name)
        document_type_text  = "TYPE: {:s}".format(custom_editor.current_file_type)
        #Initialize the tree display
        self.setSelectionBehavior(data.QAbstractItemView.SelectRows)
        tree_model = data.PyQt.QtGui.QStandardItemModel()
        tree_model.setHorizontalHeaderLabels([document_name])
        self.clean_model()
        self.setModel(tree_model)
        self.setUniformRowHeights(True)
        self.set_font_size(data.tree_display_font_size)
        #Add the file attributes to the tree display
        description_brush = data.PyQt.QtGui.QBrush(
            data.PyQt.QtGui.QColor(data.theme.Font.Python.Keyword[1])
        )
        description_font = data.PyQt.QtGui.QFont(
            "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
        )
        item_document_name  = data.PyQt.QtGui.QStandardItem(document_name_text)
        item_document_name.setEditable(False)
        item_document_name.setForeground(description_brush)
        item_document_name.setFont(description_font)
        item_document_type  = data.PyQt.QtGui.QStandardItem(document_type_text)
        item_document_type.setEditable(False)
        item_document_type.setForeground(description_brush)
        item_document_type.setFont(description_font)
        item_document_type.setIcon(self.nim_icon)
        tree_model.appendRow(item_document_name)
        tree_model.appendRow(item_document_type)
        """Add the nodes"""
        label_brush = data.PyQt.QtGui.QBrush(
            data.PyQt.QtGui.QColor(data.theme.Font.Python.SingleQuotedString[1])
        )
        label_font  = data.PyQt.QtGui.QFont(
            "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
        )
        #Nested function for creating a tree node
        def create_tree_node(node_text, 
                             node_text_brush, 
                             node_text_font, 
                             node_icon, 
                             node_line_number):
            tree_node = data.PyQt.QtGui.QStandardItem(node_text)
            tree_node.setEditable(False)
            if node_text_brush != None:
                tree_node.setForeground(node_text_brush)
            if node_text_font != None:
                tree_node.setFont(node_text_font)
            if node_icon != None:
                tree_node.setIcon(node_icon)
            if node_line_number != None:
                tree_node.line_number = node_line_number
            return tree_node
        #Nested recursive function for displaying nodes
        def show_nim_node(tree, parent_node, new_node):
            #Nested function for retrieving the nodes name attribute case insensitively
            def get_case_insensitive_name(item):
                name = item.name
                return name.lower()
            #Check if parent node is set, else append to the main tree model
            appending_node = parent_node
            if parent_node == None:
                appending_node = tree
            if new_node.imports != []:
                item_imports_node = create_tree_node("IMPORTS:", label_brush, label_font, None, None)
                appending_node.appendRow(item_imports_node)
                #Sort the list by the name attribute
                new_node.imports.sort(key=get_case_insensitive_name)
                #new_node.imports.sort(key=operator.attrgetter('name'))
                for module in new_node.imports:
                    item_module_node =  create_tree_node(
                                            module.name, 
                                            None, 
                                            None, 
                                            self.node_icon_import, 
                                            module.line + 1
                                        )
                    item_imports_node.appendRow(item_module_node)
            if new_node.types != []:
                item_types_node = create_tree_node("TYPES:", label_brush, label_font, None, None)
                appending_node.appendRow(item_types_node)
                #Sort the list by the name attribute
                new_node.types.sort(key=get_case_insensitive_name)
                for type in new_node.types:
                    item_type_node =    create_tree_node(
                                            type.name, 
                                            None, 
                                            None, 
                                            self.node_icon_type, 
                                            type.line + 1
                                        )
                    item_types_node.appendRow(item_type_node)
            if new_node.consts != []:
                item_consts_node = create_tree_node("CONSTANTS:", label_brush, label_font, None, None)
                appending_node.appendRow(item_consts_node)
                #Sort the list by the name attribute
                new_node.consts.sort(key=get_case_insensitive_name)
                for const in new_node.consts:
                    item_const_node =   create_tree_node(
                                            const.name, 
                                            None, 
                                            None, 
                                            self.node_icon_const, 
                                            const.line + 1
                                        )
                    item_consts_node.appendRow(item_const_node)
            if new_node.lets != []:
                item_lets_node = create_tree_node("SINGLE ASSIGNMENT VARIABLES:", label_brush, label_font, None, None)
                appending_node.appendRow(item_lets_node)
                #Sort the list by the name attribute
                new_node.consts.sort(key=get_case_insensitive_name)
                for let in new_node.lets:
                    item_let_node =   create_tree_node(
                                            let.name, 
                                            None, 
                                            None, 
                                            self.node_icon_const, 
                                            let.line + 1
                                        )
                    item_lets_node.appendRow(item_let_node)
            if new_node.vars != []:
                item_vars_node = create_tree_node("VARIABLES:", label_brush, label_font, None, None)
                appending_node.appendRow(item_vars_node)
                #Sort the list by the name attribute
                new_node.vars.sort(key=get_case_insensitive_name)
                for var in new_node.vars:
                    item_var_node = create_tree_node(
                                        var.name, 
                                        None, 
                                        None, 
                                        self.node_icon_variable, 
                                        var.line + 1
                                    )
                    item_vars_node.appendRow(item_var_node)
            if new_node.procedures != []:
                item_procs_node = create_tree_node("PROCEDURES:", label_brush, label_font, None, None)
                appending_node.appendRow(item_procs_node)
                #Sort the list by the name attribute
                new_node.procedures.sort(key=get_case_insensitive_name)
                for proc in new_node.procedures:
                    item_proc_node = create_tree_node(
                                        proc.name, 
                                        None, 
                                        None, 
                                        self.node_icon_procedure, 
                                        proc.line + 1
                                    )
                    item_procs_node.appendRow(item_proc_node)
                    show_nim_node(None, item_proc_node, proc)
            if new_node.forward_declarations != []:
                item_fds_node = create_tree_node("FORWARD DECLARATIONS:", label_brush, label_font, None, None)
                appending_node.appendRow(item_fds_node)
                #Sort the list by the name attribute
                new_node.forward_declarations.sort(key=get_case_insensitive_name)
                for proc in new_node.forward_declarations:
                    item_fd_node = create_tree_node(
                                        proc.name, 
                                        None, 
                                        None, 
                                        self.node_icon_procedure, 
                                        proc.line + 1
                                    )
                    item_fds_node.appendRow(item_fd_node)
                    show_nim_node(None, item_fd_node, proc)
            if new_node.converters != []:
                item_converters_node = create_tree_node("CONVERTERS:", label_brush, label_font, None, None)
                appending_node.appendRow(item_converters_node)
                #Sort the list by the name attribute
                new_node.converters.sort(key=get_case_insensitive_name)
                for converter in new_node.converters:
                    item_converter_node =   create_tree_node(
                                                converter.name, 
                                                None, 
                                                None, 
                                                self.node_icon_converter,  
                                                converter.line + 1
                                            )
                    item_converters_node.appendRow(item_converter_node)
                    show_nim_node(None, item_converter_node, converter)
            if new_node.iterators != []:
                item_iterators_node = create_tree_node("ITERATORS:", label_brush, label_font, None, None)
                appending_node.appendRow(item_iterators_node)
                #Sort the list by the name attribute
                new_node.iterators.sort(key=get_case_insensitive_name)
                for iterator in new_node.iterators:
                    item_iterator_node =   create_tree_node(
                                                iterator.name, 
                                                None, 
                                                None, 
                                                self.node_icon_iterator,  
                                                iterator.line + 1
                                            )
                    item_iterators_node.appendRow(item_iterator_node)
                    show_nim_node(None, item_iterator_node, iterator)
            if new_node.methods != []:
                item_methods_node = create_tree_node("METHODS:", label_brush, label_font, None, None)
                appending_node.appendRow(item_methods_node)
                #Sort the list by the name attribute
                new_node.methods.sort(key=get_case_insensitive_name)
                for method in new_node.methods:
                    item_method_node = create_tree_node(
                                        method.name, 
                                        None, 
                                        None, 
                                        self.node_icon_method, 
                                        method.line + 1
                                    )
                    item_methods_node.appendRow(item_method_node)
                    show_nim_node(None, item_method_node, method)
            if new_node.properties != []:
                item_properties_node = create_tree_node("PROPERTIES:", label_brush, label_font, None, None)
                appending_node.appendRow(item_properties_node)
                #Sort the list by the name attribute
                new_node.properties.sort(key=get_case_insensitive_name)
                for property in new_node.properties:
                    item_property_node = create_tree_node(
                                            property.name, 
                                            None, 
                                            None, 
                                            self.node_icon_method, 
                                            property.line + 1
                                        )
                    item_properties_node.appendRow(item_property_node)
                    show_nim_node(None, item_property_node, property)
            if new_node.macros != []:
                item_macros_node = create_tree_node("MACROS:", label_brush, label_font, None, None)
                appending_node.appendRow(item_macros_node)
                #Sort the list by the name attribute
                new_node.macros.sort(key=get_case_insensitive_name)
                for macro in new_node.macros:
                    item_macro_node = create_tree_node(
                                        macro.name, 
                                        None, 
                                        None, 
                                        self.node_icon_macro, 
                                        macro.line + 1
                                    )
                    item_macros_node.appendRow(item_macro_node)
                    show_nim_node(None, item_macro_node, macro)
            if new_node.templates != []:
                item_templates_node = create_tree_node("TEMPLATES:", label_brush, label_font, None, None)
                appending_node.appendRow(item_templates_node)
                #Sort the list by the name attribute
                new_node.templates.sort(key=get_case_insensitive_name)
                for template in new_node.templates:
                    item_template_node = create_tree_node(
                                        template.name, 
                                        None, 
                                        None, 
                                        self.node_icon_template, 
                                        template.line + 1
                                    )
                    item_templates_node.appendRow(item_template_node)
                    show_nim_node(None, item_template_node, template)
            if new_node.objects != []:
                item_classes_node = create_tree_node("OBJECTS:", label_brush, label_font, None, None)
                appending_node.appendRow(item_classes_node)
                #Sort the list by the name attribute
                new_node.objects.sort(key=get_case_insensitive_name)
                for obj in new_node.objects:
                    item_class_node = create_tree_node(
                                        obj.name, 
                                        None, 
                                        None, 
                                        self.node_icon_class, 
                                        obj.line + 1
                                    )
                    item_classes_node.appendRow(item_class_node)
                    show_nim_node(None, item_class_node, obj)
            if new_node.namespaces != []:
                item_namespaces_node = create_tree_node("NAMESPACES:", label_brush, label_font, None, None)
                appending_node.appendRow(item_namespaces_node)
                #Sort the list by the name attribute
                new_node.namespaces.sort(key=get_case_insensitive_name)
                for namespace in new_node.namespaces:
                    item_namespace_node = create_tree_node(
                                        namespace.name, 
                                        None, 
                                        None, 
                                        self.node_icon_namespace, 
                                        namespace.line + 1
                                    )
                    item_namespaces_node.appendRow(item_namespace_node)
                    show_nim_node(None, item_namespace_node, namespace)
        show_nim_node(tree_model, None, nim_nodes)
    
    def clean_model(self):
        return
        if self.model() != None:
            self.model().setParent(None)
            self.setModel(None)
    
    def _init_found_files_options(self, search_text, directory, custom_text=None):
        #Initialize the tree display to the found files type
        self.horizontalScrollbarAction(1)
        self.setSelectionBehavior(data.QAbstractItemView.SelectRows)
        tree_model = data.PyQt.QtGui.QStandardItemModel()
        tree_model.setHorizontalHeaderLabels(["FOUND FILES TREE"])
        self.header().hide()
        self.clean_model()
        self.setModel(tree_model)
        self.setUniformRowHeights(True)
        self.set_font_size(10)
        """Define the description details"""
        #Font
        description_brush = data.PyQt.QtGui.QBrush(
            data.PyQt.QtGui.QColor(data.theme.Font.Python.Keyword[1])
        )
        description_font    = data.PyQt.QtGui.QFont(
            "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
        )
        #Directory item
        item_directory  = data.PyQt.QtGui.QStandardItem(
            "BASE DIRECTORY: {:s}".format(directory.replace("\\", "/"))
        )
        item_directory.setEditable(False)
        item_directory.setForeground(description_brush)
        item_directory.setFont(description_font)
        #Search item, display according to the custom text parameter
        if custom_text == None:
            item_search_text = data.PyQt.QtGui.QStandardItem(
                "FILE HAS: {:s}".format(search_text)
            )
        else:
            item_search_text = data.PyQt.QtGui.QStandardItem(custom_text)
        item_search_text.setEditable(False)
        item_search_text.setForeground(description_brush)
        item_search_text.setFont(description_font)
        tree_model.appendRow(item_directory)
        tree_model.appendRow(item_search_text)
        return tree_model
    
    def _init_replace_in_files_options(self, search_text, replace_text, directory):
        #Initialize the tree display to the found files type
        self.horizontalScrollbarAction(1)
        self.setSelectionBehavior(data.QAbstractItemView.SelectRows)
        tree_model = data.PyQt.QtGui.QStandardItemModel()
        tree_model.setHorizontalHeaderLabels(["REPLACED IN FILES TREE"])
        self.header().hide()
        self.clean_model()
        self.setModel(tree_model)
        self.setUniformRowHeights(True)
        self.set_font_size(data.tree_display_font_size)
        """Define the description details"""
        #Font
        description_brush = data.PyQt.QtGui.QBrush(
            data.PyQt.QtGui.QColor(data.theme.Font.Python.Default[1])
        )
        description_font = data.PyQt.QtGui.QFont(
            "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
        )
        #Directory item
        item_directory  = data.PyQt.QtGui.QStandardItem(
            "BASE DIRECTORY: {:s}".format(directory.replace("\\", "/"))
        )
        item_directory.setEditable(False)
        item_directory.setForeground(description_brush)
        item_directory.setFont(description_font)
        #Search item
        item_search_text = data.PyQt.QtGui.QStandardItem(
                            "SEARCH TEXT: {:s}".format(search_text)
                           )
        item_search_text.setEditable(False)
        item_search_text.setForeground(description_brush)
        item_search_text.setFont(description_font)
        #Replace item
        item_replace_text = data.PyQt.QtGui.QStandardItem(
                            "REPLACE TEXT: {:s}".format(replace_text)
                           )
        item_replace_text.setEditable(False)
        item_replace_text.setForeground(description_brush)
        item_replace_text.setFont(description_font)
        tree_model.appendRow(item_directory)
        tree_model.appendRow(item_search_text)
        tree_model.appendRow(item_replace_text)
        return tree_model
    
    def _sort_item_list(self, items, base_directory):
        """
        Helper function for sorting a file/directory list so that
        all of the directories are before any files in the list
        """
        sorted_directories = []
        sorted_files = []
        for item in items:
            dir = os.path.dirname(item)
            if (not dir in sorted_directories):
                sorted_directories.append(dir)
            if os.path.isfile(item):
                sorted_files.append(item)
        #Remove the base directory from the directory list, it is not needed
        if base_directory in sorted_directories:
            sorted_directories.remove(base_directory)
        #Sort the two lists case insensitively
        sorted_directories.sort(key=str.lower)
        sorted_files.sort(key=str.lower)
        #Combine the file and directory lists
        sorted_items = sorted_directories + sorted_files
        return sorted_items
    
    def _add_items_to_tree(self, tree_model, directory, items):
        """ Helper function for adding files to a tree view """
        #Check if any files were found
        if items != []:
            #Set the UNIX file format to the directory
            directory = directory.replace("\\", "/")
            """Adding the files"""
            label_brush = data.PyQt.QtGui.QBrush(
                data.PyQt.QtGui.QColor(data.theme.Font.Python.SingleQuotedString[1])
            )
            label_font = data.PyQt.QtGui.QFont(
                "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
            )
            item_brush = data.PyQt.QtGui.QBrush(
                data.PyQt.QtGui.QColor(data.theme.Font.Python.Default[1])
            )
            item_font = data.PyQt.QtGui.QFont("Courier", data.tree_display_font_size)
            #Create the base directory item that will hold all of the found files
            item_base_directory = data.PyQt.QtGui.QStandardItem(directory)
            item_base_directory.setEditable(False)
            item_base_directory.setForeground(label_brush)
            item_base_directory.setFont(label_font)
            item_base_directory.setIcon(self.folder_icon)
            #Add an indicating attribute that shows the item is a directory.
            #It's a python object, attributes can be added dynamically!
            item_base_directory.is_base = True
            item_base_directory.full_name = directory
            #Create the base directory object that will hold everything else
            base_directory = self.Directory(item_base_directory)
            #Create the files that will be added last directly to the base directory
            base_files = {}
            #Sort the the item list so that all of the directories are before the files
            sorted_items = self._sort_item_list(items, directory)
            #Loop through the files while creating the directory tree
            for item_with_path in sorted_items:
                if os.path.isfile(item_with_path):
                    file = item_with_path.replace(directory, "")
                    file_name       = os.path.basename(file)
                    directory_name  = os.path.dirname(file)
                    #Strip the first "/" from the files directory
                    if directory_name.startswith("/"):
                        directory_name = directory_name[1:]
                    #Initialize the file item
                    item_file = data.PyQt.QtGui.QStandardItem(file_name)
                    item_file.setEditable(False)
                    item_file.setForeground(item_brush)
                    item_file.setFont(item_font)
                    file_type = functions.get_file_type(file_name)
                    item_file.setIcon(functions.get_language_file_icon(file_type))
                    #Add an atribute that will hold the full file name to the QStandartItem.
                    #It's a python object, attributes can be added dynamically!
                    item_file.full_name = item_with_path
                    #Check if the file is in the base directory
                    if directory_name == "":
                        #Store the file item for adding to the bottom of the tree
                        base_files[file_name] = item_file
                    else:
                        #Check the previous file items directory structure
                        parsed_directory_list = directory_name.split("/")
                        #Create the new directories
                        current_directory = base_directory
                        for dir in parsed_directory_list:
                            #Check if the current loop directory already exists
                            if dir in current_directory.directories:
                                current_directory = current_directory.directories[dir]
                        #Add the file to the directory
                        current_directory.add_file(file_name, item_file)
                else:
                    directory_name  = item_with_path.replace(directory, "")
                    #Strip the first "/" from the files directory
                    if directory_name.startswith("/"):
                        directory_name = directory_name[1:]
                    #Check the previous file items directory structure
                    parsed_directory_list = directory_name.split("/")
                    #Create the new directories
                    current_directory = base_directory
                    for dir in parsed_directory_list:
                        #Check if the current loop directory already exists
                        if dir in current_directory.directories:
                            current_directory = current_directory.directories[dir]
                        else:
                            #Create the new directory item
                            item_new_directory = data.PyQt.QtGui.QStandardItem(dir)
                            item_new_directory.setEditable(False)
                            item_new_directory.setIcon(self.folder_icon)
                            item_new_directory.setForeground(item_brush)
                            item_new_directory.setFont(item_font)
                            #Add an indicating attribute that shows the item is a directory.
                            #It's a python object, attributes can be added dynamically!
                            item_new_directory.is_dir = True
                            item_new_directory.full_name = item_with_path
                            current_directory = current_directory.add_directory(
                                dir, 
                                item_new_directory
                            )
            #Add the base level files from the stored dictionary, first sort them
            for file_key in sorted(base_files, key=str.lower):
                base_directory.add_file(file_key, base_files[file_key])
            tree_model.appendRow(item_base_directory)
            #Expand the base directory item
            self.expand(item_base_directory.index())
            #Resize the header so the horizontal scrollbar will have the correct width
            self.resize_horizontal_scrollbar()
        else:
            item_no_files_found = data.PyQt.QtGui.QStandardItem("No items found")
            item_no_files_found.setEditable(False)
            item_no_files_found.setIcon(self.node_icon_nothing)
            item_no_files_found.setForeground(label_brush)
            item_no_files_found.setFont(label_font)
            tree_model.appendRow(item_no_files_found)
    
    def _add_items_with_lines_to_tree(self, tree_model, directory, items):
        """ Helper function for adding files to a tree view """
        #Check if any files were found
        if items != {}:
            #Set the UNIX file format to the directory
            directory = directory.replace("\\", "/")
            """Adding the files"""
            label_brush = data.PyQt.QtGui.QBrush(
                data.PyQt.QtGui.QColor(data.theme.Font.Python.SingleQuotedString[1])
            )
            label_font  = data.PyQt.QtGui.QFont(
                "Courier", data.tree_display_font_size, data.PyQt.QtGui.QFont.Bold
            )
            item_brush = data.PyQt.QtGui.QBrush(
                data.PyQt.QtGui.QColor(data.theme.Font.Python.Default[1])
            )
            item_font = data.PyQt.QtGui.QFont("Courier", data.tree_display_font_size)
            #Create the base directory item that will hold all of the found files
            item_base_directory = data.PyQt.QtGui.QStandardItem(directory)
            item_base_directory.setEditable(False)
            item_base_directory.setForeground(label_brush)
            item_base_directory.setFont(label_font)
            item_base_directory.setIcon(self.folder_icon)
            #Create the base directory object that will hold everything else
            base_directory = self.Directory(item_base_directory)
            #Create the files that will be added last directly to the base directory
            base_files = {}
            #Sort the the item list so that all of the directories are before the files
            items_list = list(items.keys())
            sorted_items = self._sort_item_list(items_list, directory)
            #Loop through the files while creating the directory tree
            for item_with_path in sorted_items:
                if os.path.isfile(item_with_path):
                    file = item_with_path.replace(directory, "")
                    file_name       = os.path.basename(file)
                    directory_name  = os.path.dirname(file)
                    #Strip the first "/" from the files directory
                    if directory_name.startswith("/"):
                        directory_name = directory_name[1:]
                    #Initialize the file item
                    item_file = data.PyQt.QtGui.QStandardItem(file_name)
                    item_file.setEditable(False)
                    file_type = functions.get_file_type(file_name)
                    item_file.setIcon(functions.get_language_file_icon(file_type))
                    item_file.setForeground(item_brush)
                    item_file.setFont(item_font)
                    #Add an atribute that will hold the full file name to the QStandartItem.
                    #It's a python object, attributes can be added dynamically!
                    item_file.full_name = item_with_path
                    for line in items[item_with_path]:
                        #Adjust the line numbering to Ex.Co. (1 to end)
                        line += 1
                        #Create the goto line item
                        item_line = data.PyQt.QtGui.QStandardItem("line {:d}".format(line))
                        item_line.setEditable(False)
                        item_line.setIcon(self.goto_icon)
                        item_line.setForeground(item_brush)
                        item_line.setFont(item_font)
                        #Add the file name and line number as attributes
                        item_line.full_name     = item_with_path
                        item_line.line_number   = line
                        item_file.appendRow(item_line)
                    #Check if the file is in the base directory
                    if directory_name == "":
                        #Store the file item for adding to the bottom of the tree
                        base_files[file_name] = item_file
                    else:
                        #Check the previous file items directory structure
                        parsed_directory_list = directory_name.split("/")
                        #Create the new directories
                        current_directory = base_directory
                        for dir in parsed_directory_list:
                            #Check if the current loop directory already exists
                            if dir in current_directory.directories:
                                current_directory = current_directory.directories[dir]
                        #Add the file to the directory
                        current_directory.add_file(file_name, item_file)
                else:
                    directory_name  = item_with_path.replace(directory, "")
                    #Strip the first "/" from the files directory
                    if directory_name.startswith("/"):
                        directory_name = directory_name[1:]
                    #Check the previous file items directory structure
                    parsed_directory_list = directory_name.split("/")
                    #Create the new directories
                    current_directory = base_directory
                    for dir in parsed_directory_list:
                        #Check if the current loop directory already exists
                        if dir in current_directory.directories:
                            current_directory = current_directory.directories[dir]
                        else:
                            #Create the new directory item
                            item_new_directory = data.PyQt.QtGui.QStandardItem(dir)
                            item_new_directory.setEditable(False)
                            item_new_directory.setIcon(self.folder_icon)
                            item_new_directory.setForeground(item_brush)
                            item_new_directory.setFont(item_font)
                            #Add an indicating attribute that shows the item is a directory.
                            #It's a python object, attributes can be added dynamically!
                            item_new_directory.is_dir = True
                            current_directory = current_directory.add_directory(
                                                    dir, 
                                                    item_new_directory
                                                )
            #Add the base level files from the stored dictionary, first sort them
            for file_key in sorted(base_files, key=str.lower):
                base_directory.add_file(file_key, base_files[file_key])
            tree_model.appendRow(item_base_directory)
            #Expand the base directory item
            self.expand(item_base_directory.index())
            #Resize the header so the horizontal scrollbar will have the correct width
            self.resize_horizontal_scrollbar()
        else:
            item_no_files_found = data.PyQt.QtGui.QStandardItem("No items found")
            item_no_files_found.setEditable(False)
            item_no_files_found.setIcon(self.node_icon_nothing)
            item_no_files_found.setForeground(item_brush)
            item_no_files_found.setFont(item_font)
            tree_model.appendRow(item_no_files_found)
    
    def display_directory_tree(self, directory):
        """
        Display the selected directory in a tree view structure
        """
        #Set the tree display type to FILES
        self.set_display_type(data.TreeDisplayType.FILES)
        #Create the walk generator that returns all files/subdirectories
        try:
            walk_generator = os.walk(directory)
        except:
            self.main_form.display.repl_display_message(
                "Invalid directory!", 
                message_type=data.MessageType.ERROR
            )
            return
        #Initialize and display the search options
        tree_model = self._init_found_files_options(
            None, 
            directory, 
            custom_text="DISPLAYING ALL FILES/SUBDIRECTORIES"
        )
        #Initialize the list that will hold both the directories and files
        found_items = []
        for item in walk_generator:
            base_directory = item[0]
            for dir in item[1]:
                found_items.append(os.path.join(base_directory, dir).replace("\\", "/"))
            for file in item[2]:
                found_items.append(os.path.join(base_directory, file).replace("\\", "/"))
        #Add the items to the treeview
        self._add_items_to_tree(tree_model, directory, found_items)
    
    def display_found_files(self, search_text, found_files, directory):
        """
        Display files that were found using the 'functions' module's
        find_files function
        """
        #Check if found files are valid
        if found_files == None:
            self.main_form.display.repl_display_message(
                "Error in finding files!", 
                message_type=data.MessageType.WARNING
            )
            return
        #Set the tree display type to FILES
        self.set_display_type(data.TreeDisplayType.FILES)
        #Initialize and display the search options
        tree_model = self._init_found_files_options(search_text, directory)
        #Sort the found file list
        found_files.sort(key=str.lower)
        #Add the items to the treeview
        self._add_items_to_tree(tree_model, directory, found_files)
    
    def display_found_files_with_lines(self, search_text, found_files, directory):
        """
        Display files with lines that were found using the 'functions' 
        module's find_in_files function
        """
        #Check if found files are valid
        if found_files == None:
            self.main_form.display.repl_display_message(
                "Error in finding files!", 
                message_type=data.MessageType.WARNING
            )
            return
        #Set the tree display type to NODE
        self.set_display_type(data.TreeDisplayType.FILES_WITH_LINES)
        #Initialize and display the search options
        tree_model = self._init_found_files_options(search_text, directory)
        #Add the items with lines to the treeview
        self._add_items_with_lines_to_tree(tree_model, directory, found_files)
    
    def display_replacements_in_files(self, 
                                      search_text, 
                                      replace_text, 
                                      replaced_files, 
                                      directory):
        """
        Display files with lines that were replaces using the 'functions' 
        module's replace_text_in_files_enum function
        """
        #Check if found files are valid
        if replaced_files == None:
            self.main_form.display.repl_display_message(
                "Error in finding files!", 
                message_type=data.MessageType.WARNING
            )
            return
        #Set the tree display type to NODE
        self.set_display_type(data.TreeDisplayType.FILES_WITH_LINES)
        #Initialize and display the search options
        tree_model = self._init_replace_in_files_options(search_text, replace_text, directory)
        #Add the items with lines to the treeview
        self._add_items_with_lines_to_tree(tree_model, directory, replaced_files)




"""
----------------------------------------------------------------------------
Object for displaying text difference between two files
----------------------------------------------------------------------------
"""
class TextDiffer(data.QWidget):
    """A widget that holds two PlainEditors for displaying text difference"""
    #Class variables
    parent                  = None
    main_form               = None
    name                    = ""
    savable                 = data.CanSave.NO
    current_icon            = None
    icon_manipulator        = None
    focused_editor          = None
    text_1                  = None
    text_2                  = None
    text_1_name             = None
    text_2_name             = None
    #Class constants
    DEFAULT_FONT            = data.PyQt.QtGui.QFont('Courier', 10)
    MARGIN_STYLE            = data.PyQt.Qsci.QsciScintilla.STYLE_LINENUMBER
    INDICATOR_UNIQUE_1          = 1
    Indicator_Unique_1_Color    = data.PyQt.QtGui.QColor(0x72, 0x9f, 0xcf, 80)
    INDICATOR_UNIQUE_2          = 2
    Indicator_Unique_2_Color    = data.PyQt.QtGui.QColor(0xad, 0x7f, 0xa8, 80)
    INDICATOR_SIMILAR           = 3
    Indicator_Similar_Color     = data.PyQt.QtGui.QColor(0x8a, 0xe2, 0x34, 80)
    GET_X_OFFSET    = data.PyQt.Qsci.QsciScintillaBase.SCI_GETXOFFSET
    SET_X_OFFSET    = data.PyQt.Qsci.QsciScintillaBase.SCI_SETXOFFSET
    UPDATE_H_SCROLL = data.PyQt.Qsci.QsciScintillaBase.SC_UPDATE_H_SCROLL
    UPDATE_V_SCROLL = data.PyQt.Qsci.QsciScintillaBase.SC_UPDATE_V_SCROLL
    #Diff icons
    icon_unique_1   = None
    icon_unique_2   = None
    icon_similar    = None
    #Marker references
    marker_unique_1         = None
    marker_unique_2         = None
    marker_unique_symbol_1  = None
    marker_unique_symbol_2  = None
    marker_similar_1        = None
    marker_similar_2        = None
    marker_similar_symbol_1 = None
    marker_similar_symbol_2 = None
    #Child widgets
    splitter    = None
    editor_1    = None
    editor_2    = None
    layout      = None
    find_toolbar= None
    
        
    def clean_up(self):
        self.editor_1.mousePressEvent = None
        self.editor_1.wheelEvent = None
        self.editor_2.mousePressEvent = None
        self.editor_2.wheelEvent = None
        self.editor_1.actual_parent = None
        self.editor_2.actual_parent = None
        self.editor_1.clean_up()
        self.editor_2.clean_up()
        self.editor_1 = None
        self.editor_2 = None
        if self.find_toolbar != None:
            self.find_toolbar.setParent(None)
            self.find_toolbar = None
        self.focused_editor = None
        self.splitter.setParent(None)
        self.splitter = None
        self.layout = None
        self.parent = None
        self.main_form = None
        self.icon_manipulator = None
        # Clean up self
        self.setParent(None)
        self.deleteLater()
        """
        The actual clean up will occur when the next garbage collection
        cycle is executed, probably because of the nested functions and 
        the focus decorator.
        """
    
    def __init__(self, 
                 parent, 
                 main_form, 
                 text_1=None, 
                 text_2=None, 
                 text_1_name="", 
                 text_2_name=""):
        """Initialization"""
        # Initialize the superclass
        super().__init__(parent)
        # Initialize components
        self.icon_manipulator = components.IconManipulator()
        # Initialize colors according to theme
        self.Indicator_Unique_1_Color = data.theme.TextDifferColors.Indicator_Unique_1_Color
        self.Indicator_Unique_2_Color = data.theme.TextDifferColors.Indicator_Unique_2_Color
        self.Indicator_Similar_Color = data.theme.TextDifferColors.Indicator_Similar_Color
        # Store the reference to the parent
        self.parent = parent
        # Store the reference to the main form
        self.main_form = main_form
        # Set the differ icon
        self.current_icon = functions.create_icon('tango_icons/compare-text.png')
        #Set the name of the differ widget
        if text_1_name != None and text_2_name != None:
            self.name = "Text difference: {:s} / {:s}".format(text_1_name, text_2_name)
            self.text_1_name = text_1_name
            self.text_2_name = text_2_name
        else:
            self.name = "Text difference"
            self.text_1_name = "TEXT 1"
            self.text_2_name = "TEXT 2"
        # Initialize diff icons
        self.icon_unique_1  = functions.create_icon("tango_icons/diff-unique-1.png")
        self.icon_unique_2  = functions.create_icon("tango_icons/diff-unique-2.png")
        self.icon_similar   = functions.create_icon("tango_icons/diff-similar.png")
        # Create the horizontal splitter and two editor widgets
        self.splitter = data.QSplitter(data.PyQt.QtCore.Qt.Horizontal, self)
        self.editor_1 = forms.CustomEditor(self, main_form)
        self.init_editor(self.editor_1)
        self.editor_2 = forms.CustomEditor(self, main_form)
        self.init_editor(self.editor_2)
        self.editor_1.choose_lexer("text")
        self.editor_2.choose_lexer("text")
        self.splitter.addWidget(self.editor_1)
        self.splitter.addWidget(self.editor_2)
        self.layout = data.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.splitter)
        # Set the layout
        self.setLayout(self.layout)
        # Connect the necessary signals
        self.editor_1.SCN_UPDATEUI.connect(self._scn_updateui_1)
        self.editor_2.SCN_UPDATEUI.connect(self._scn_updateui_2)
        self.editor_1.cursorPositionChanged.connect(self._cursor_change_1)
        self.editor_2.cursorPositionChanged.connect(self._cursor_change_2)
        # Overwrite the CustomEditor parent widgets to point to the TextDiffers' PARENT
        self.editor_1.parent = self.parent
        self.editor_2.parent = self.parent
        # Add a new attribute to the CustomEditor that will hold the TextDiffer reference
        self.editor_1.actual_parent = self
        self.editor_2.actual_parent = self
        # Set the embedded flag
        self.editor_1.embedded = True
        self.editor_2.embedded = True
        # Add decorators to each editors mouse clicks and mouse wheel scrolls
        def focus_decorator(function_to_decorate, focused_editor):
            def decorated_function(*args, **kwargs):
                self.focused_editor = focused_editor
                function_to_decorate(*args, **kwargs)
            return decorated_function
        self.editor_1.mousePressEvent = focus_decorator(
            self.editor_1.mousePressEvent,
            self.editor_1
        )
        self.editor_1.wheelEvent = focus_decorator(
            self.editor_1.wheelEvent,
            self.editor_1
        )
        self.editor_2.mousePressEvent = focus_decorator(
            self.editor_2.mousePressEvent,
            self.editor_2
        )
        self.editor_2.wheelEvent = focus_decorator(
            self.editor_2.wheelEvent,
            self.editor_2
        )
        # Focus the first editor on initialization
        self.focused_editor = self.editor_1
        self.focused_editor.setFocus()
        # Initialize markers
        self.init_markers()
        # Set the theme
        self.set_theme(data.theme)
        # Set editor functions that have to be propagated from the TextDiffer
        # to the child editor
        self._init_editor_functions()
        # Check the text validity
        if text_1 == None or text_2 == None:
            #One of the texts is unspecified
            return
        # Create the diff
        self.compare(text_1, text_2)
    
    def _scn_updateui_1(self, sc_update):
        """Function connected to the SCN_UPDATEUI signal for scroll detection"""
        if self.focused_editor == self.editor_1:
            #Scroll the opposite editor
            if sc_update == self.UPDATE_H_SCROLL:
                current_x_offset = self.editor_1.SendScintilla(self.GET_X_OFFSET)
                self.editor_2.SendScintilla(self.SET_X_OFFSET, current_x_offset)
            elif sc_update == self.UPDATE_V_SCROLL:
                current_top_line = self.editor_1.firstVisibleLine()
                self.editor_2.setFirstVisibleLine(current_top_line)
    
    def _scn_updateui_2(self, sc_update):
        """Function connected to the SCN_UPDATEUI signal for scroll detection"""
        if self.focused_editor == self.editor_2:
            #Scroll the opposite editor
            if sc_update == self.UPDATE_H_SCROLL:
                current_x_offset = self.editor_2.SendScintilla(self.GET_X_OFFSET)
                self.editor_1.SendScintilla(self.SET_X_OFFSET, current_x_offset)
            elif sc_update == self.UPDATE_V_SCROLL:
                current_top_line = self.editor_2.firstVisibleLine()
                self.editor_1.setFirstVisibleLine(current_top_line)
    
    def _cursor_change_1(self, line, index):
        """
        Function connected to the cursorPositionChanged signal for
        cursor position change detection
        """
        if self.focused_editor == self.editor_1:
            #Update the cursor position on the opposite editor
            cursor_line, cursor_index = self.editor_1.getCursorPosition()
            #Check if the opposite editor line is long enough
            if self.editor_2.lineLength(cursor_line) > cursor_index:
                self.editor_2.setCursorPosition(cursor_line, cursor_index)
            else:
                self.editor_2.setCursorPosition(cursor_line, 0)
            #Update the first visible line, so that the views in both differs match
            current_top_line = self.editor_1.firstVisibleLine()
            self.editor_2.setFirstVisibleLine(current_top_line)
    
    def _cursor_change_2(self, line, index):
        """
        Function connected to the cursorPositionChanged signal for
        cursor position change detection
        """
        if self.focused_editor == self.editor_2:
            #Update the cursor position on the opposite editor
            cursor_line, cursor_index = self.editor_2.getCursorPosition()
            #Check if the opposite editor line is long enough
            if self.editor_1.lineLength(cursor_line) > cursor_index:
                self.editor_1.setCursorPosition(cursor_line, cursor_index)
            else:
                self.editor_1.setCursorPosition(cursor_line, 0)
            #Update the first visible line, so that the views in both differs match
            current_top_line = self.editor_2.firstVisibleLine()
            self.editor_1.setFirstVisibleLine(current_top_line)
    
    def _update_margins(self):
        """Update the text margin width"""
        self.editor_1.setMarginWidth(0, "0" * len(str(self.editor_1.lines())))
        self.editor_2.setMarginWidth(0, "0" * len(str(self.editor_2.lines())))
    
    def _signal_editor_cursor_change(self, cursor_line=None, cursor_column=None):
        """Signal that fires when cursor position changes in one of the editors"""
        self.main_form.display.update_cursor_position(cursor_line, cursor_column)
    
    def _init_editor_functions(self):
        """
        Initialize the editor functions that are called on the TextDiffer widget,
        but need to be executed on one of the editors
        """
        #Find text function propagated to the focused editor
        def enabled_function(*args, **kwargs):
            #Get the function
            function = getattr(self.focused_editor, args[0])
            #Call the function˘, leaving out the "function name" argument
            function(*args[1:], **kwargs)
        #Unimplemented functions
        def uniplemented_function(*args, **kwargs):
            self.main_form.display.repl_display_message(
                "Function '{:s}' is not implemented by the TextDiffer!".format(args[0]), 
                message_type=data.MessageType.ERROR
            )
        all_editor_functions = inspect.getmembers(
            forms.CustomEditor, 
            predicate=inspect.isfunction
        )
        skip_functions = [
            "set_theme",
            "clean_up",
        ]
        enabled_functions = [
            "find_text",
        ]
        disabled_functions = [
            "__init__",
            "__setattr__",
            "_filter_keypress",
            "_filter_keyrelease",
            "_init_special_functions",
            "_set_indicator",
            "find_text",
            "keyPressEvent",
            "keyReleaseEvent",
            "mousePressEvent",
            "setFocus",
            "wheelEvent",
        ]
        #Check methods
        for function in all_editor_functions:
            if function[0] in skip_functions:
                #Use the TextDiffer implementation of this function
                continue
            if function[0] in enabled_functions:
                #Find text is enabled
                setattr(
                    self, 
                    function[0], 
                    functools.partial(enabled_function, function[0])
                )
            elif function[0] in disabled_functions:
                #Disabled functions should be skipped, they are probably already
                #implemented by the TextDiffer
                continue
            else:
                #Unimplemented functions should display an error message
                setattr(
                    self, 
                    function[0], 
                    functools.partial(uniplemented_function, function[0])
                )
        
    def mousePressEvent(self, event):
        """Overloaded mouse click event"""
        #Execute the superclass mouse click event
        super().mousePressEvent(event)
        #Set focus to the clicked editor
        self.setFocus()
        #Set the last focused widget to the parent basic widget
        self.main_form.last_focused_widget = self.parent
        data.print_log("Stored \"{:s}\" as last focused widget".format(self.parent.name))
        #Hide the function wheel if it is shown
        if self.main_form.view.function_wheel_overlay != None:
            self.main_form.view.hide_function_wheel()
        # Reset the click&drag context menu action
        components.ActionFilter.clear_action()
    
    def setFocus(self):
        """Overridden focus event"""
        #Execute the superclass focus function
        super().setFocus()
        #Check indication
        self.main_form.view.indication_check()
        #Focus the last focused editor
        self.focused_editor.setFocus()
    
    def init_margin(self, 
                    editor, 
                    marker_unique, 
                    marker_unique_symbol, 
                    marker_similar, 
                    marker_similar_symbol):
        """Initialize margin for coloring lines showing diff symbols"""
        editor.setMarginWidth(0, "0")
        #Setting the margin width to 0 makes the marker colour the entire line
        #to the marker background color
        editor.setMarginWidth(1, "00")
        editor.setMarginWidth(2, 0)        
        editor.setMarginType(0, data.PyQt.Qsci.QsciScintilla.TextMargin)
        editor.setMarginType(1, data.PyQt.Qsci.QsciScintilla.SymbolMargin)
        editor.setMarginType(2, data.PyQt.Qsci.QsciScintilla.SymbolMargin)
        #I DON'T KNOW THE ENTIRE LOGIC BEHIND MARKERS AND MARGINS! If you set 
        #something wrong in the margin mask, the markers on a different margin don't appear!
        #http://www.scintilla.org/ScintillaDoc.html#SCI_SETMARGINMASKN
        editor.setMarginMarkerMask(
            1,
            ~data.PyQt.Qsci.QsciScintillaBase.SC_MASK_FOLDERS 
        )
        editor.setMarginMarkerMask(
            2, 
            0x0
        )
    
    def init_markers(self):
        """Initialize all markers for showing diff symbols"""
        #Set the images
        image_scale_size = data.PyQt.QtCore.QSize(16, 16)
        image_unique_1  = functions.create_pixmap('tango_icons/diff-unique-1.png')
        image_unique_2  = functions.create_pixmap('tango_icons/diff-unique-2.png')
        image_similar   = functions.create_pixmap('tango_icons/diff-similar.png')
        #Scale the images to a smaller size
        image_unique_1  = image_unique_1.scaled(image_scale_size)
        image_unique_2  = image_unique_2.scaled(image_scale_size)
        image_similar   = image_similar.scaled(image_scale_size)
        #Markers for editor 1
        self.marker_unique_1            = self.editor_1.markerDefine(data.PyQt.Qsci.QsciScintillaBase.SC_MARK_BACKGROUND, 0)
        self.marker_unique_symbol_1     = self.editor_1.markerDefine(image_unique_1, 1)
        self.marker_similar_1           = self.editor_1.markerDefine(data.PyQt.Qsci.QsciScintillaBase.SC_MARK_BACKGROUND, 2)
        self.marker_similar_symbol_1    = self.editor_1.markerDefine(image_similar, 3)
        #Set background colors only for the background markers
        self.editor_1.setMarkerBackgroundColor(self.Indicator_Unique_1_Color, self.marker_unique_1)
        self.editor_1.setMarkerBackgroundColor(self.Indicator_Similar_Color, self.marker_similar_1)
        #Margins for editor 1
        self.init_margin(
            self.editor_1, 
            self.marker_unique_1, 
            self.marker_unique_symbol_1, 
            self.marker_similar_1, 
            self.marker_similar_symbol_1
        )
        #Markers for editor 2
        self.marker_unique_2            = self.editor_2.markerDefine(data.PyQt.Qsci.QsciScintillaBase.SC_MARK_BACKGROUND, 0)
        self.marker_unique_symbol_2     = self.editor_2.markerDefine(image_unique_2, 1)
        self.marker_similar_2           = self.editor_2.markerDefine(data.PyQt.Qsci.QsciScintillaBase.SC_MARK_BACKGROUND, 2)
        self.marker_similar_symbol_2    = self.editor_2.markerDefine(image_similar, 3)
        #Set background colors only for the background markers
        self.editor_2.setMarkerBackgroundColor(self.Indicator_Unique_2_Color, self.marker_unique_2)
        self.editor_2.setMarkerBackgroundColor(self.Indicator_Similar_Color, self.marker_similar_2)
        #Margins for editor 2
        self.init_margin(
            self.editor_2, 
            self.marker_unique_2, 
            self.marker_unique_symbol_2, 
            self.marker_similar_2, 
            self.marker_similar_symbol_2
        )
    
    def init_indicator(self,
                       editor, 
                       indicator, 
                       color):
        """Set the indicator settings"""
        editor.indicatorDefine(
            data.PyQt.Qsci.QsciScintillaBase.INDIC_ROUNDBOX,
            indicator
        )
        editor.setIndicatorForegroundColor(
            color, 
            indicator
        )
        editor.SendScintilla(
            data.PyQt.Qsci.QsciScintillaBase.SCI_SETINDICATORCURRENT, 
            indicator
        )
    
    def init_editor(self, editor):
        """Initialize all of the PlainEditor settings for difference displaying"""
        editor.setLexer(None)
        editor.setUtf8(True)
        editor.setIndentationsUseTabs(False)
        editor.setFont(self.DEFAULT_FONT)
        editor.setBraceMatching(data.PyQt.Qsci.QsciScintilla.SloppyBraceMatch)
        editor.setMatchedBraceBackgroundColor(data.PyQt.QtGui.QColor(255, 153, 0))
        editor.setAcceptDrops(False)
        editor.setEolMode(data.default_eol)
        editor.setReadOnly(True)
        editor.savable = data.CanSave.NO
    
    def set_margin_text(self, editor, line, text):
        """Set the editor's margin text at the selected line"""
        editor.setMarginText(line, text, self.MARGIN_STYLE)
    
    def set_line_indicator(self, editor, line, indicator_index):
        """Set the editor's selected line color"""
        #Set the indicator
        if indicator_index == self.INDICATOR_UNIQUE_1:
            self.init_indicator(
                editor, 
                self.INDICATOR_UNIQUE_1, 
                self.Indicator_Unique_1_Color
            )
        elif indicator_index == self.INDICATOR_UNIQUE_2:
            self.init_indicator(
                editor, 
                self.INDICATOR_UNIQUE_2, 
                self.Indicator_Unique_2_Color
            )
        elif indicator_index == self.INDICATOR_SIMILAR:
            self.init_indicator(
                editor, 
                self.INDICATOR_SIMILAR, 
                self.Indicator_Similar_Color
            )
        #Color the line background
        scintilla_command = data.PyQt.Qsci.QsciScintillaBase.SCI_INDICATORFILLRANGE
        start   = editor.positionFromLineIndex(line, 0)
        length  = editor.lineLength(line)
        editor.SendScintilla(
            scintilla_command, 
            start, 
            length
        )
    
    def compare(self, text_1, text_2):
        """
        Compare two text strings and display the difference
        !! This function uses Python's difflib which is not 100% accurate !!
        """
        #Store the original text
        self.text_1 = text_1
        self.text_2 = text_2
        text_1_list = text_1.split("\n")
        text_2_list = text_2.split("\n")
        #Create the difference
        differer = difflib.Differ()
        list_sum = list(differer.compare(text_1_list, text_2_list))
        #Assemble the two lists of strings that will be displayed in each editor
        list_1              = []
        line_counter_1      = 1
        line_numbering_1    = []
        line_styling_1      = []
        list_2              = []
        line_counter_2      = 1
        line_numbering_2    = []
        line_styling_2      = []
        #Flow control flags
        skip_next     = False
        store_next    = False
        for i, line in enumerate(list_sum):
            if store_next == True:
                store_next = False
                list_2.append(line[2:])
                line_numbering_2.append(str(line_counter_2))
                line_counter_2 += 1
                line_styling_2.append(self.INDICATOR_SIMILAR)
            elif skip_next == False:
                if line.startswith("  "):
                    #The line is the same in both texts
                    list_1.append(line[2:])
                    line_numbering_1.append(str(line_counter_1))
                    line_counter_1 += 1
                    line_styling_1.append(None)
                    list_2.append(line[2:])
                    line_numbering_2.append(str(line_counter_2))
                    line_counter_2 += 1
                    line_styling_2.append(None)
                elif line.startswith("- "):
                    #The line is unique to text 1
                    list_1.append(line[2:])
                    line_numbering_1.append(str(line_counter_1))
                    line_counter_1 += 1
                    line_styling_1.append(self.INDICATOR_UNIQUE_1)
                    list_2.append("")
                    line_numbering_2.append("")
                    line_styling_2.append(None)
                elif line.startswith("+ "):
                    #The line is unique to text 2
                    list_1.append("")
                    line_numbering_1.append("")
                    line_styling_1.append(None)
                    list_2.append(line[2:])
                    line_numbering_2.append(str(line_counter_2))
                    line_counter_2 += 1
                    line_styling_2.append(self.INDICATOR_UNIQUE_2)
                elif line.startswith("? "):
                    #The line is similar
                    if (list_sum[i-1].startswith("- ") and
                        list_sum[i+1].startswith("+ ") and
                        list_sum[i+2].startswith("? ")):
                        """
                        Line order:
                            - ...
                            ? ...
                            + ...
                            ? ...
                        """
                        #Lines have only a few character difference, skip the 
                        #first '?' and handle the next '?' as a "'- '/'+ '/'? '" sequence
                        pass
                    elif list_sum[i-1].startswith("- "):
                        #Line in text 1 has something added
                        """
                        Line order:
                            - ...
                            ? ...
                            + ...
                        """
                        line_styling_1[len(line_numbering_1) - 1] = self.INDICATOR_SIMILAR
                        
                        list_2.pop()
                        line_numbering_2.pop()
                        line_styling_2.pop()
                        store_next = True
                    elif list_sum[i-1].startswith("+ "):
                        #Line in text 2 has something added
                        """
                        Line order:
                            - ...
                            + ...
                            ? ...
                        """
                        list_1.pop()
                        line_numbering_1.pop()
                        line_styling_1.pop()
                        line_styling_1[len(line_numbering_1) - 1] = self.INDICATOR_SIMILAR
                        
                        pop_index_2 = (len(line_numbering_2) - 1) - 1
                        list_2.pop(pop_index_2)
                        line_numbering_2.pop(pop_index_2)
                        line_styling_2.pop()
                        line_styling_2.pop()
                        line_styling_2.append(self.INDICATOR_SIMILAR)
            else:
                skip_next = False
        #Display the results
        self.editor_1.setText("\n".join(list_1))
        self.editor_2.setText("\n".join(list_2))
        #Set margins and style for both editors
        for i, line in enumerate(line_numbering_1):
            self.set_margin_text(self.editor_1, i, line)
            line_styling = line_styling_1[i]
            if line_styling != None:
                if line_styling == self.INDICATOR_SIMILAR:
                    self.editor_1.markerAdd(i, self.marker_similar_1)
                    self.editor_1.markerAdd(i, self.marker_similar_symbol_1)
                else:
                    self.editor_1.markerAdd(i, self.marker_unique_1)
                    self.editor_1.markerAdd(i, self.marker_unique_symbol_1)
        for i, line in enumerate(line_numbering_2):
            self.set_margin_text(self.editor_2, i, line)
            line_styling = line_styling_2[i]
            if line_styling != None:
                if line_styling == self.INDICATOR_SIMILAR:
                    self.editor_2.markerAdd(i, self.marker_similar_2)
                    self.editor_2.markerAdd(i, self.marker_similar_symbol_2)
                else:
                    self.editor_2.markerAdd(i, self.marker_unique_2)
                    self.editor_2.markerAdd(i, self.marker_unique_symbol_2)
        #Check if there were any differences
        if (any(line_styling_1) == False and any(line_styling_2) == False):
            self.main_form.display.repl_display_message(
                "No differences between texts.", 
                message_type=data.MessageType.SUCCESS
            )
        else:
            #Count the number of differences
            difference_counter_1 = 0
            #Similar line count is the same in both editor line stylings
            similarity_counter = 0
            for diff in line_styling_1:
                if diff != None:
                    if diff == self.INDICATOR_SIMILAR:
                        similarity_counter += 1
                    else:
                        difference_counter_1 += 1
            difference_counter_2 = 0
            for diff in line_styling_2:
                if diff != None:
                    if diff == self.INDICATOR_SIMILAR:
                        #Skip the similar line, which were already counter above
                        continue
                    else:
                        difference_counter_2 += 1
            #Display the differences/similarities messages
            self.main_form.display.repl_display_message(
                "{:d} differences found in '{:s}'!".format(difference_counter_1, self.text_1_name), 
                message_type=data.MessageType.DIFF_UNIQUE_1
            )
            self.main_form.display.repl_display_message(
                "{:d} differences found in '{:s}'!".format(difference_counter_2, self.text_2_name), 
                message_type=data.MessageType.DIFF_UNIQUE_2
            )
            self.main_form.display.repl_display_message(
                "{:d} similarities found between documents!".format(similarity_counter, self.text_2_name), 
                message_type=data.MessageType.DIFF_SIMILAR
            )
        self._update_margins()
    
    def find_next_unique_1(self):
        """Find and scroll to the first unique 1 difference"""
        self.focused_editor         = self.editor_1
        cursor_line, cursor_index   = self.editor_1.getCursorPosition()
        next_unique_diff_line = self.editor_1.markerFindNext(cursor_line+1, 0b0011)
        #Correct the line numbering to the 1..line_count display
        next_unique_diff_line += 1
        self.editor_1.goto_line(next_unique_diff_line, skip_repl_focus=False)
        self.editor_2.goto_line(next_unique_diff_line, skip_repl_focus=False)
        #Check if we are back at the start of the document
        if next_unique_diff_line == 0:
            self.main_form.display.repl_display_message(
                "Scrolled back to the start of the document!", 
                message_type=data.MessageType.DIFF_UNIQUE_1
            )
            self.main_form.display.write_to_statusbar(
                "Scrolled back to the start of the document!"
            )
    
    def find_next_unique_2(self):
        """Find and scroll to the first unique 2 difference"""
        self.focused_editor         = self.editor_2
        cursor_line, cursor_index   = self.editor_2.getCursorPosition()
        next_unique_diff_line = self.editor_2.markerFindNext(cursor_line+1, 0b0011)
        #Correct the line numbering to the 1..line_count display
        next_unique_diff_line += 1
        self.editor_1.goto_line(next_unique_diff_line, skip_repl_focus=False)
        self.editor_2.goto_line(next_unique_diff_line, skip_repl_focus=False)
        #Check if we are back at the start of the document
        if next_unique_diff_line == 0:
            self.main_form.display.repl_display_message(
                "Scrolled back to the start of the document!", 
                message_type=data.MessageType.DIFF_UNIQUE_2
            )
            self.main_form.display.write_to_statusbar(
                "Scrolled back to the start of the document!"
            )
    
    def find_next_similar(self):
        """Find and scroll to the first similar line"""
        self.focused_editor         = self.editor_1
        cursor_line, cursor_index   = self.editor_1.getCursorPosition()
        next_unique_diff_line = self.editor_1.markerFindNext(cursor_line+1, 0b1100)
        #Correct the line numbering to the 1..line_count display
        next_unique_diff_line += 1
        self.editor_1.goto_line(next_unique_diff_line, skip_repl_focus=False)
        self.editor_2.goto_line(next_unique_diff_line, skip_repl_focus=False)
        #Check if we are back at the start of the document
        if next_unique_diff_line == 0:
            self.main_form.display.repl_display_message(
                "Scrolled back to the start of the document!", 
                message_type=data.MessageType.DIFF_SIMILAR
            )
            self.main_form.display.write_to_statusbar(
                "Scrolled back to the start of the document!"
            )
    
    def show_find_buttons(self, parent):
        """
        Create and display buttons for finding unique/similar differences
        on the parent basic widget
        """
        # Check if the parent is a basic widget
        if isinstance(parent, forms.BasicWidget) == False:
            return
        # Clean up the toolbar if needed
        if self.find_toolbar != None:
            self.find_toolbar.setParent(None)
            self.find_toolbar = None
        # Create the find toolbar and buttons
        self.find_toolbar = data.QToolBar(parent)
        self.find_toolbar.setIconSize(data.PyQt.QtCore.QSize(16,16))
        unique_1_action = data.QAction(
            functions.create_icon("tango_icons/diff-unique-1.png"), 
            "unique_1_button",
            parent
        )
        unique_1_action.setToolTip(
            "Scroll to next unique line\nin document: '{:s}'".format(self.text_1_name)
        )
        unique_1_action.triggered.connect(self.find_next_unique_1)
        unique_2_action =   data.QAction(
            functions.create_icon("tango_icons/diff-unique-2.png"), 
            "unique_2_button",
            parent
        )
        unique_2_action.setToolTip(
            "Scroll to next unique line\nin document: '{:s}'".format(self.text_2_name)
        )
        unique_2_action.triggered.connect(self.find_next_unique_2)
        similar_action = data.QAction(
            functions.create_icon("tango_icons/diff-similar.png"), 
            "unique_2_button",
            parent
        )
        similar_action.setToolTip(
            "Scroll to next similar line\nin both documents"
        )
        similar_action.triggered.connect(self.find_next_similar)
        self.find_toolbar.addAction(unique_1_action)
        self.find_toolbar.addAction(unique_2_action)
        self.find_toolbar.addAction(similar_action)
        self.find_toolbar.show()
        # Set the corner widget of the parent
        parent.setCornerWidget(self.find_toolbar)
    
    def set_theme(self, theme):
        def set_editor_theme(editor):
            if theme == themes.Air:
                editor.resetFoldMarginColors()
            elif theme == themes.Earth:
                editor.setFoldMarginColors(
                    theme.FoldMargin.ForeGround, 
                    theme.FoldMargin.BackGround
                )
            editor.setMarginsForegroundColor(theme.LineMargin.ForeGround)
            editor.setMarginsBackgroundColor(theme.LineMargin.BackGround)
            editor.SendScintilla(
                data.PyQt.Qsci.QsciScintillaBase.SCI_STYLESETBACK, 
                data.PyQt.Qsci.QsciScintillaBase.STYLE_DEFAULT, 
                theme.Paper.Default
            )
            editor.SendScintilla(
                data.PyQt.Qsci.QsciScintillaBase.SCI_STYLESETBACK, 
                data.PyQt.Qsci.QsciScintillaBase.STYLE_LINENUMBER, 
                theme.LineMargin.BackGround
            )
            editor.SendScintilla(
                data.PyQt.Qsci.QsciScintillaBase.SCI_SETCARETFORE, 
                theme.Cursor
            )
            editor.choose_lexer("text")
        set_editor_theme(self.editor_1)
        set_editor_theme(self.editor_2)



"""
----------------------------------------------------------------------------
Object for showing log messages across all widgets, mostly for debug purposes
----------------------------------------------------------------------------
"""
class MessageLogger(data.QWidget):
    """Simple subclass for displaying log messages"""
    class MessageTextBox(data.QTextEdit): 
        def contextMenuEvent(self, event):
            event.accept()
    
    #Controls and variables of the log window  (class variables >> this means that these variables are shared accross instances of this class)
    displaybox  = None      #QTextEdit that will display log messages
    layout      = None      #The layout of the log window
    parent      = None
    
    def __init__(self, parent):
        """Initialization routine"""
        #Initialize superclass, from which the current class is inherited, THIS MUST BE DONE SO THAT THE SUPERCLASS EXECUTES ITS __init__ !!!!!!
        super().__init__()
        
        #Initialize the log window
        self.setWindowTitle("LOGGING WINDOW")
        self.resize(500, 300)
        self.setWindowFlags(data.PyQt.QtCore.Qt.WindowStaysOnTopHint)
        
        #Initialize the display box
        self.displaybox = MessageLogger.MessageTextBox(self)
        self.displaybox.setReadOnly(True)
        #Make displaybox click/doubleclick event also fire the log window click/doubleclick method
        self.displaybox.mousePressEvent         = self._event_mousepress
        self.displaybox.mouseDoubleClickEvent   = self._event_mouse_doubleclick
        self.keyPressEvent                      = self._keypress
        
        #Initialize layout
        self.layout = data.QGridLayout()
        self.layout.addWidget(self.displaybox)
        self.setLayout(self.layout)
        
        self.append_message("Ex.Co. debug log window loaded")
        self.append_message("LOGGING Mode is enabled")
        self.parent = parent
        
        #Set the log window icon
        if os.path.isfile(data.application_icon) == True:
            self.setWindowIcon(data.PyQt.QtGui.QIcon(data.application_icon))
    
    def _event_mouse_doubleclick(self, mouse_event):
        """Rereferenced/overloaded displaybox doubleclick event"""
        self.clear_log()
    
    def _event_mousepress(self, mouse_event):
        """Rereferenced/overloaded displaybox click event"""
        # Reset the click&drag context menu action
        components.ActionFilter.clear_action()
    
    def _keypress(self, key_event):
        """Rereferenced/overloaded MessageLogger keypress event"""
        pressed_key = key_event.key()
        if pressed_key == data.PyQt.QtCore.Qt.Key_Escape:
            self.close()
    
    def clear_log(self):
        """Clear all messages from the log display"""
        self.displaybox.clear()
        
    def append_message(self, *args, **kwargs):
        """Adds a message as a string to the log display if logging mode is enabled"""
        if len(args) > 1:
            message = " ".join(args)
        else:
            message = args[0]
        #Check if message is a string class, if not then make it a string
        if isinstance(message, str) == False:
            message = str(message)
        #Check if logging mode is enabled
        if data.logging_mode == True:
            self.displaybox.append(message)
        #Bring cursor to the current message (this is in a QTextEdit not QScintilla)
        cursor = self.displaybox.textCursor()
        cursor.movePosition(data.PyQt.QtGui.QTextCursor.End)
        cursor.movePosition(data.PyQt.QtGui.QTextCursor.StartOfLine)
        self.displaybox.setTextCursor(cursor)



"""
-----------------------------------------------------------------------------------
ExCo Information Widget for displaying the license, used languages and libraries, ...
-----------------------------------------------------------------------------------
"""
class ExCoInfo(data.QDialog):
    #Class variables
    name    = "Ex.Co. Info"
    savable = data.CanSave.NO
    
    #Class functions(methods)
    def __init__(self, parent, app_dir=""):
        """Initialization routine"""
        #Initialize superclass, from which the current class is inherited,
        #THIS MUST BE DONE SO THAT THE SUPERCLASS EXECUTES ITS __init__ !!!!!!
        super().__init__()
        #Setup the window
        self.setWindowTitle("About Ex.Co.")
        self.setWindowFlags(data.PyQt.QtCore.Qt.WindowStaysOnTopHint)
        #Setup the picture
        exco_picture = data.PyQt.QtGui.QPixmap(data.about_image)
        self.picture = data.QLabel(self)
        self.picture.setPixmap(exco_picture)
        self.picture.setGeometry(self.frameGeometry())
        self.picture.setScaledContents(True)
        #Assign events
        self.picture.mousePressEvent        = self._close
        self.picture.mouseDoubleClickEvent  = self._close
        #Initialize layout
        self.layout = data.QGridLayout()
        self.layout.addWidget(self.picture)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(
            data.PyQt.QtCore.QMargins(0,0,0,0)
        )
        self.setLayout(self.layout)
        #Set the log window icon
        if os.path.isfile(data.application_icon) == True:
            self.setWindowIcon(data.PyQt.QtGui.QIcon(data.application_icon))
        #Save the info window geometry, the values were gotten by showing a dialog with the label containing
        #the ExCo info image with the size set to (50, 50), so it would automatically resize to the label image size
        my_width    = 610
        my_height   = 620
        #Set the info window position
        parent_left     = parent.geometry().left()
        parent_top      = parent.geometry().top()
        parent_width    = parent.geometry().width()
        parent_height   = parent.geometry().height()
        my_left = parent_left + (parent_width/2) - (my_width/2)
        my_top = parent_top + (parent_height/2) - (my_height/2)
        self.setGeometry(data.PyQt.QtCore.QRect(my_left, my_top, my_width, my_height))
        self.setFixedSize(my_width, my_height)
#        self.setStyleSheet("background-color:transparent;")
#        self.setWindowFlags(data.PyQt.QtCore.Qt.WindowStaysOnTopHint | data.PyQt.QtCore.Qt.Dialog | data.PyQt.QtCore.Qt.FramelessWindowHint)
#        self.setAttribute(data.PyQt.QtCore.Qt.WA_TranslucentBackground)
    
    def _close(self, event):
        """Close the widget"""
        self.picture.setParent(None)
        self.picture = None
        self.layout = None
        self.close()

"""
-----------------------------------------------------------------------------------
Custom buttons used by the FunctionWheelOverlay and ContextMenu in the forms module
-----------------------------------------------------------------------------------
"""
class CustomButton(data.QLabel):
    """
    Custom button used for displaying and executing Ex.Co. functions
    """
    #Class variables
    parent              = None
    group_box_parent    = None
    main_form           = None
    stored_pixmap       = None
    stored_font         = None
    stored_hex          = None
    function            = None
    function_text       = None
    stored_opacity      = 0.0
    focus_last_widget   = True
    no_tab_focus_disable       = False
    no_document_focus_disable  = True
    check_last_tab_type = False
    check_text_differ   = None
    tool_tip            = None
    scale               = (1, 1)
    # Class constants
    OPACITY_LOW         = 0.5
    OPACITY_HIGH        = 1.0
    """
    This was measured by hand
    """
    INNER_IMAGE_OFFSET  = (18, 13)
    """
    This should be the actual pixel dimensions of the hex image file
    """
    HEX_IMAGE_SIZE      = (68, 60)
    
    
    def __init__(self, 
                 parent, 
                 main_form,
                 input_pixmap, 
                 input_function=None, 
                 input_function_text="", 
                 input_font=data.PyQt.QtGui.QFont(
                 'Courier', 14, weight=data.PyQt.QtGui.QFont.Bold
                 ), 
                 input_focus_last_widget=data.HexButtonFocus.NONE, 
                 input_no_tab_focus_disable=False, 
                 input_no_document_focus_disable=True, 
                 input_check_last_tab_type=False, 
                 input_check_text_differ=False, 
                 input_tool_tip=None,
                 input_scale=(1, 1)):
        #Initialize superclass
        super().__init__(parent)
        #Store the reference to the parent
        self.parent = parent
        #Store the reference to the main form
        self.main_form = main_form
        #Store the reference to the group box that holds the parent
        #(the parent of the parent)
        self.group_box_parent = parent.parent
        #Store the main function image
        self.stored_pixmap = input_pixmap
        #Store the hex edge image
        self.stored_hex = data.PyQt.QtGui.QPixmap(
            os.path.join(
                data.resources_directory, 
                "various/hex-button-edge.png"
            )
        )
        #Store the function that will be executed on the click event
        self.function = input_function
        #Store the function text
        self.function_text = input_function_text
        #Set the attribute that will be check if focus update is needed
        #when the custom button executes its function
        self.focus_last_widget = input_focus_last_widget
        #Set the attribute that checks if any tab is focused
        self.no_tab_focus_disable = input_no_tab_focus_disable
        #Set the attribute that will be check if button will be disabled
        #if there is no focused document tab
        self.no_document_focus_disable = input_no_document_focus_disable
        #Set checking the save state stored in the main form
        self.check_last_tab_type = input_check_last_tab_type
        #Set checking for if the focused tab is a text differer
        self.check_text_differ = input_check_text_differ
        #Set the font that will be used with the button
        self.stored_font = input_font
        #Enable mouse move events
        self.setMouseTracking(True)
        #Set the image for displaying
        self.setPixmap(input_pixmap)
        #Image should scale to the button size
        self.setScaledContents(True)
        # Set the button mask, which sets the button area to the shape of
        # the button image instead of a rectangle
        self.setMask(self.stored_hex.mask())
        #Set the initial opacity to low
        self._set_opacity(self.OPACITY_LOW)
        #Set the tooltip if it was set
        if input_tool_tip != None:
            self.setToolTip(input_tool_tip)
        # Set the scaling
        self.scale = input_scale

    def _set_opacity(self, input_opacity):
        """Set the opacity of the stored QPixmap image and display it"""
        # Store the opacity
        self.stored_opacity = input_opacity
        # Create and initialize the QImage from the stored QPixmap
        button_image = self.stored_pixmap
        # Resize the button image to scale
        button_image = button_image.scaled(
            data.PyQt.QtCore.QSize(
                math.ceil(button_image.size().width() * self.scale[0]),
                math.ceil(button_image.size().height() * self.scale[1]),
            ),
            transformMode=data.PyQt.QtCore.Qt.SmoothTransformation
        )
        # Scale the hex image
        hex_image = self.stored_hex
        scaled_size = data.PyQt.QtCore.QSize(
            math.ceil(hex_image.size().width() * self.scale[0]),
            math.ceil(hex_image.size().height() * self.scale[1]),
        )
        image = data.PyQt.QtGui.QImage(
            scaled_size, #hex_image.size(), 
            data.PyQt.QtGui.QImage.Format_ARGB32_Premultiplied
        )
        image.fill(data.PyQt.QtCore.Qt.transparent)
        # Create and initialize the QPainter that will manipulate the QImage
        button_painter = data.PyQt.QtGui.QPainter(image)
        button_painter.setOpacity(input_opacity)
        # Adjust inner button positioning according to the scale
        x_scaled = math.ceil(self.scale[0] * self.INNER_IMAGE_OFFSET[0])
        y_scaled = math.ceil(self.scale[1] * self.INNER_IMAGE_OFFSET[1])
        button_painter.drawPixmap(x_scaled, y_scaled, button_image)
        button_painter.end()
        # Display the manipulated image
        self.setPixmap(data.PyQt.QtGui.QPixmap.fromImage(image))
        # Set the button mask, which sets the button area to the shape of
        # the button image instead of a rectangle
        self.setMask(hex_image.mask())
    
    def _set_opacity_with_hex_edge(self, input_opacity):
        """
        Set the opacity of the stored QPixmap image and display it
        """
        # Store the opacity
        self.stored_opacity = input_opacity
        # Create and initialize the QImage from the stored QPixmap
        button_image = self.stored_pixmap
        # Resize the button image to scale
        button_image = button_image.scaled(
            data.PyQt.QtCore.QSize(
                math.ceil(button_image.size().width() * self.scale[0]),
                math.ceil(button_image.size().height() * self.scale[1]),
            ),
            transformMode=data.PyQt.QtCore.Qt.SmoothTransformation
        )
        # Scale the hex image
        hex_image = self.stored_hex
        scaled_size = data.PyQt.QtCore.QSize(
            math.ceil(hex_image.size().width() * self.scale[0]),
            math.ceil(hex_image.size().height() * self.scale[1]),
        )
        image = data.PyQt.QtGui.QImage(
            scaled_size, #hex_image.size(), 
            data.PyQt.QtGui.QImage.Format_ARGB32_Premultiplied
        )
        image.fill(data.PyQt.QtCore.Qt.transparent)
        # Create and initialize the QPainter that will manipulate the QImage
        button_painter = data.PyQt.QtGui.QPainter(image)
        button_painter.setCompositionMode(data.PyQt.QtGui.QPainter.CompositionMode_Source)
        button_painter.setOpacity(input_opacity)
        # Resize the hex image to scale
        hex_image = hex_image.scaled(
            data.PyQt.QtCore.QSize(
                math.ceil(hex_image.size().width() * self.scale[0]),
                math.ceil(hex_image.size().height() * self.scale[1]),
            ),
            transformMode=data.PyQt.QtCore.Qt.SmoothTransformation
        )
        # Adjust inner button positioning according to the scale
        button_painter.drawPixmap(0, 0, hex_image)
        x_scaled = math.ceil(self.scale[0] * self.INNER_IMAGE_OFFSET[0])
        y_scaled = math.ceil(self.scale[1] * self.INNER_IMAGE_OFFSET[1])
        button_painter.drawPixmap(x_scaled, y_scaled, button_image)
        button_painter.end()
        # Display the manipulated image
        self.setPixmap(data.PyQt.QtGui.QPixmap.fromImage(image))
        # Set the button mask, which sets the button area to the shape of
        # the button image instead of a rectangle
        self.setMask(hex_image.mask())
    
    def set_offset(self, offset):
        self.setGeometry(
            offset[0], 
            offset[1], 
            math.ceil(self.scale[0] * self.HEX_IMAGE_SIZE[0]), 
            math.ceil(self.scale[0] * self.HEX_IMAGE_SIZE[1])
        )
    
    def mousePressEvent(self, event):
        """Overloaded widget click event"""
        #Execute the superclass mouse click event first
        super().mousePressEvent(event)
        #Execute the function if it was initialized
        if self.function != None:
            try:
                #Set focus to the last focused widget stored on the main form
                if self.focus_last_widget == data.HexButtonFocus.TAB:
                    self.main_form.last_focused_widget.currentWidget().setFocus()
                elif self.focus_last_widget == data.HexButtonFocus.WINDOW:
                    self.main_form.last_focused_widget.setFocus()
                #Store the executed function for next cursor placement
                self.main_form.view.last_executed_function_text = self.function_text
                #Execute the buttons stored function
                self.function()
            except:
                traceback.print_exc()
                message = "You need to focus one of the editor windows first!"
                self.main_form.display.repl_display_message(
                    message, 
                    message_type=data.MessageType.ERROR
                )
            #Close the function wheel
            self.parent.hide()
    
    def mouseMoveEvent(self, event):
        """Overloaded mouse move event"""
        super().mouseMoveEvent(event)
        if self.isEnabled() == True:
            self.highlight()
    
    def enterEvent(self, event):
        """Overloaded widget enter event"""
        super().enterEvent(event)
        #Bring the widget to the front of the Z-axis stack
        self.raise_()
        #Highlight the widget only if it's enabled
        if self.isEnabled() == True:
            self.highlight()
    
    def leaveEvent(self, event):
        """Overloaded widget leave event"""
        super().leaveEvent(event)
        #Dim the widget only if it's enabled
        if self.isEnabled() == True:
            self.dim()
    
    def dim(self, clear_hex_edge=False):
        """Set the buttons opacity to low and clear the function text"""
        #Set the opacity to low
        if clear_hex_edge == True:
            self._set_opacity(self.OPACITY_LOW)
        else:
            self._set_opacity_with_hex_edge(self.OPACITY_LOW)
        #Clear the text in the parent display label
        self.parent.display("", self.stored_font)
    
    def highlight(self):
        """Set the buttons opacity to high and display the buttons function text"""
        #Set the opacity to full
        self._set_opacity_with_hex_edge(self.OPACITY_HIGH)
        #Display the stored function text
        self.parent.display(self.function_text, self.stored_font)

class DoubleButton(CustomButton):
    """
    A CustomButton with an extra button added to itself,
    used for when double functionality is needed, for example when
    a function has a version with or without a dialog window.
    """
    #The extra button reference
    parent                      = None
    main_form                   = None
    extra_button                = None
    extra_button_size_factor    = 1/3
    extra_button_position       = data.PyQt.QtCore.QPoint(0, 0)
    extra_button_stored_opacity = None
    extra_button_stored_pixmap  = None
    extra_button_function       = None
    extra_button_function_text  = None
    #Class constants
    OPACITY_LOW                 = 0.5
    OPACITY_HIGH                = 1.0
    
    def init_extra_button(self, 
                          parent, 
                          main_form, 
                          input_extra_pixmap, 
                          input_extra_function=None, 
                          input_extra_function_text=""):   
        #Store the parent and main form references
        self.parent     = parent
        self.main_form  = main_form
        #Initialize the extra button
        self.extra_button = data.QLabel(self)
        width   = int(self.geometry().width() * self.extra_button_size_factor)
        height  = int(self.geometry().height() * self.extra_button_size_factor)
        self.extra_button_position = data.PyQt.QtCore.QPoint(
                                        self.geometry().width()*2/3-width, 
                                        self.geometry().height()*1/4
                                        )
        rectangle   = data.PyQt.QtCore.QRect(self.extra_button_position, data.PyQt.QtCore.QSize(width, height))
        self.extra_button.setGeometry(rectangle)
        self.extra_button_stored_pixmap = input_extra_pixmap
        self.extra_button.setPixmap(input_extra_pixmap)
        self.extra_button.setScaledContents(True)
        #Store the function options
        self.extra_button_function      = input_extra_function
        self.extra_button_function_text = input_extra_function_text
        #Set the extra button opacity to low
        self._set_extra_button_opacity(self.OPACITY_LOW)
        #Overridden the extra buttons events
        self.extra_button.mousePressEvent   = self.extra_button_click
        self.extra_button.enterEvent        = self.extra_button_enter_event
        self.extra_button.leaveEvent        = self.extra_button_leave_event
    
    def extra_button_click(self, event):
        """mousePressEvent for the extra button"""
        #Execute the function if it was initialized
        if self.extra_button_function != None:
            try:
                #Set focus to the last focused widget stored on the main form
                if self.focus_last_widget == data.HexButtonFocus.TAB:
                    self.main_form.last_focused_widget.currentWidget().setFocus()
                elif self.focus_last_widget == data.HexButtonFocus.WINDOW:
                    self.main_form.last_focused_widget.setFocus()
                #Store the executed function for next cursor placement
                self.main_form.view.last_executed_function_text = self.function_text
                #Execute the buttons stored function
                self.extra_button_function()
            except Exception as ex:
                print(ex)
                message = "You need to focus one of the editor windows first!"
                self.main_form.display.repl_display_message(
                    message, 
                    message_type=data.MessageType.ERROR
                )
            #Close the function wheel
            self.parent.hide()
    
    def extra_button_enter_event(self, event):
        """Overloaded widget enter event"""
        #Check if the button is enabled
        if self.isEnabled() == True:
            self._set_extra_button_opacity(self.OPACITY_HIGH)
            #Display the stored extra buttons function text
            extra_button_font = data.PyQt.QtGui.QFont(
                'Courier', 
                self.stored_font.pointSize()-2, 
                weight=data.PyQt.QtGui.QFont.Bold
            )
            self.parent.display(
                self.extra_button_function_text, 
                extra_button_font
            )
    
    def extra_button_leave_event(self, event):
        """Overloaded widget enter event"""
        #Check if the button is enabled
        if self.isEnabled() == True:
            self._set_extra_button_opacity(self.OPACITY_LOW)
            #Clear the function text
            extra_button_font = data.PyQt.QtGui.QFont(
                'Courier', 
                self.stored_font.pointSize()-2, 
                weight=data.PyQt.QtGui.QFont.Bold
            )
            self.parent.display(
                "", 
                extra_button_font
            )
    
    def extra_button_enable(self):
        """Hide and disable the extra button"""
        self.extra_button.setVisible(True)
        self.extra_button.setEnabled(True)
    
    def extra_button_disable(self):
        """Hide and disable the extra button"""
        self.extra_button.setVisible(False)
        self.extra_button.setEnabled(False)
        self._set_extra_button_opacity(self.OPACITY_LOW)
    
    def resizeEvent(self, event):
        """Overridden resize event"""
        #Execute the superclass resize function
        super().resizeEvent(event)
        #Update the extra button geometry
        width = int(self.geometry().width() * self.extra_button_size_factor)
        height = int(self.geometry().height() * self.extra_button_size_factor)
        rectangle   = data.PyQt.QtCore.QRect(
                        self.extra_button_position, 
                        data.PyQt.QtCore.QSize(width, height)
                        )
        self.extra_button.setGeometry(rectangle)
    
    def _set_extra_button_opacity(self, input_opacity):
        """Set the opacity of the extra button"""
        #Store the opacity
        self.extra_button_stored_opacity = input_opacity
        #Create and initialize the QImage from the stored QPixmap
        button_image = self.extra_button_stored_pixmap
        image = data.PyQt.QtGui.QImage(
            button_image.size(), 
            data.PyQt.QtGui.QImage.Format_ARGB32_Premultiplied
        )
        image.fill(data.PyQt.QtCore.Qt.transparent)
        #Create and initialize the QPainter that will manipulate the QImage
        button_painter = data.PyQt.QtGui.QPainter(image)
        button_painter.setOpacity(input_opacity)
        button_painter.drawPixmap(0, 0, button_image)
        button_painter.end()
        #Display the manipulated image
        self.extra_button.setPixmap(data.PyQt.QtGui.QPixmap.fromImage(image))


"""
---------------------------------------------------------
Custom context menu for the editors and REPL
---------------------------------------------------------
""" 
class ContextMenu(data.QGroupBox):
    class ContextButton(CustomButton):
        """
        Subclassed custom button
        """
        # The button's number in the context menu
        number = None
        
        def _fill_background_color(self):
            self.setAutoFillBackground(True)
            p = self.palette()
            p.setColor(self.backgroundRole(), data.PyQt.QtCore.Qt.white)
            self.setPalette(p)
        
        def _set_opacity(self, input_opacity):
            super()._set_opacity(input_opacity)
            self._fill_background_color()
        
        def _set_opacity_with_hex_edge(self, input_opacity):
            super()._set_opacity_with_hex_edge(input_opacity)
            self._fill_background_color()
        
        def mousePressEvent(self, event):
            """Overloaded widget click event"""
            button = event.button()
            if button == data.PyQt.QtCore.Qt.LeftButton:
                # Execute the function if it was initialized
                if self.function != None:
                    if components.ActionFilter.click_drag_action != None:
                        function_name = components.ActionFilter.click_drag_action.function.__name__
#                        print(self.number, function_name)
                        if self.parent.functions_type == "standard":
                            ContextMenu.standard_buttons[self.number] = function_name
                        elif self.parent.functions_type == "plain":
                            ContextMenu.standard_buttons[self.number] = function_name
                        elif self.parent.functions_type == "horizontal":
                            ContextMenu.horizontal_buttons[self.number] = function_name
                        elif self.parent.functions_type == "special":
                            ContextMenu.special_buttons[self.number] = function_name
                        # Show the newly added function
                        message = "Added function '{}' at button number {}".format(
                            components.ActionFilter.click_drag_action.text(),
                            self.number
                        )
                        self.main_form.display.repl_display_message(
                            message, 
                            message_type=data.MessageType.SUCCESS
                        )
                        # Reset cursor and stored action
                        data.application.restoreOverrideCursor()
                        components.ActionFilter.click_drag_action = None
                    else:
                        try:
                            # Execute the buttons stored function
                            self.function()
                        except:
                            traceback.print_exc()
                            message = "You need to focus one of the editor windows first!"
                            self.main_form.display.repl_display_message(
                                message, 
                                message_type=data.MessageType.ERROR
                            )
                    # Close the function wheel
                    self.parent.hide()
                    event.accept()
                else:
                    event.ignore()
            elif button == data.PyQt.QtCore.Qt.RightButton:
                # Close the function wheel
                self.parent.hide()
                event.accept()
            else:
                event.ignore()
        
        def dim(self, clear_hex_edge=False):
            """Set the buttons opacity to low and clear the function text"""
            # Set the opacity to low
            if clear_hex_edge == True:
                self._set_opacity(self.OPACITY_LOW)
            else:
                self._set_opacity_with_hex_edge(self.OPACITY_LOW)
        
        def highlight(self):
            """Set the buttons opacity to high and display the buttons function text"""
            # Set the opacity to full
            self._set_opacity_with_hex_edge(self.OPACITY_HIGH)
            # Display the stored function text
            self.main_form.display.write_to_statusbar(self.function_text)
    
    # Various references
    main_form = None
    # Painting offset
    offset = (0, 0)
    # Stored menu button
    button_list = None
    # Functions dictionary
    function_list = {}
    # Inner button positions, clockwise from the top, 
    # last position is in the middle
    inner_button_positions = [
        (-27, -24, 0),
        (14, 0, 1),
        (14, 48, 2),
        (-27, 72, 3),
        (-68, 48, 4),
        (-68, 0, 5),
        (-27, 24, 6)
    ]
    outer_button_positions = [
        (-27, -72, 7),
        (14, -48, 8),
        (54, -24, 9),
        (54, 24, 10),
        (54, 72, 11),
        (14, 96, 12),
        (-27, 120, 13),
        (-68, 96, 14),
        (-108, 72, 15),
        (-108, 24, 16),
        (-108, -24, 17),
        (-68, -48, 18),
    ]
    horizontal_button_positions = [
        (-148, 0, 19),
        (-108, 24, 20),
        (-68, 0, 21),
        (-27, 24, 22),
        (14, 0, 23),
        (54, 24, 24),
        (94, 0, 25),
    ]
    standard_buttons = {
        0: "copy",
        1: "cut",
        2: "paste",
        3: "line_copy",
        4: "undo",
        5: "redo",
        6: "line_duplicate",
        7: "line_transpose",
        8: "line_cut",
        9: "line_delete",
        10: "select_all",
        11: "special_to_uppercase",
        12: "special_to_lowercase",
        13: "show_edge",
        14: "toggle_line_endings",
        15: "goto_to_end",
        16: "goto_to_start",
        17: "special_indent_to_cursor",
        18: "reset_zoom",
    }
    # A Copy for when the functions need to be reset
    stored_standard_buttons = dict(standard_buttons) # or standard_buttons[:]
    special_buttons = {
        0: "copy",
        1: "cut",
        2: "paste",
        3: "line_copy",
        4: "undo",
        5: "redo",
        6: "line_duplicate",
        7: "line_transpose",
        8: "line_cut",
        9: "line_delete",
        10: "select_all",
        11: "special_to_uppercase",
        12: "special_to_lowercase",
        13: "comment_uncomment",
        14: "toggle_line_endings",
        15: "goto_to_end",
        16: "goto_to_start",
        17: "special_indent_to_cursor",
        18: "create_node_tree",
    }
    # A Copy for when the functions need to be reset
    stored_special_buttons = dict(special_buttons) # or special_buttons[:]
    horizontal_buttons = {
        19: "copy",
        20: "cut",
        21: "paste",
        22: "comment_uncomment",
        23: "undo",
        24: "redo",
        25: "line_duplicate",
    }
    # A Copy for when the functions need to be reset
    stored_horizontal_buttons = dict(horizontal_buttons) # or horizontal_buttons[:]
    # Button scaling factor
    x_scale = 0.7
    y_scale = 0.7
    # Total button position offset
    total_offset = (0, -48)
    # Current context menu functions type
    functions_type = None
    
    def __init__(self, parent=None, main_form=None, offset=(0, 0)):
        # Initialize the superclass
        super().__init__(parent)
        # Store the reference to the parent
        self.setParent(parent)
        # Store the reference to the main form
        self.main_form = main_form
        # Store the painting offset
        self.offset = offset
        # Set the background color
        style_sheet = "background-color: transparent;"
        style_sheet += "border: 0 px;"
        self.setStyleSheet(style_sheet)
        # Set the groupbox size
        screen_resolution = data.application.desktop().screenGeometry()
        width, height = screen_resolution.width(), screen_resolution.height()
        self.setGeometry(
            data.PyQt.QtCore.QRect(0, 0, width, height)
        )
    
    @staticmethod
    def reset_functions():
        """
        Copy stored functions back into the active menu functions
        """
        ContextMenu.standard_buttons = dict(ContextMenu.stored_standard_buttons)
        ContextMenu.special_buttons = dict(ContextMenu.stored_special_buttons)
        ContextMenu.horizontal_buttons = dict(ContextMenu.stored_horizontal_buttons)
    
    @staticmethod
    def get_settings():
        """
        Return the custom function settings for the settings manipulator
        """
        return {
            "standard_buttons": ContextMenu.standard_buttons,
            "special_buttons": ContextMenu.special_buttons,
            "horizontal_buttons": ContextMenu.horizontal_buttons,
        }
    
    def check_position_offset(self, 
                              inner_buttons=True, 
                              outer_buttons=True,
                              horizontal_buttons=False):
        button_positions = []
        if inner_buttons == True:
            button_positions.extend(ContextMenu.inner_button_positions)
        if outer_buttons == True:
            button_positions.extend(ContextMenu.outer_button_positions)
        if horizontal_buttons == True:
            button_positions.extend(self.horizontal_button_positions)
        hex_x_size = self.ContextButton.HEX_IMAGE_SIZE[0] * self.x_scale
        hex_y_size = self.ContextButton.HEX_IMAGE_SIZE[1] * self.y_scale
        window_size = self.parent().size() - data.PyQt.QtCore.QSize(hex_x_size, hex_y_size)
        min_x = 0
        min_y = 0
        max_x = 0
        max_y = 0
        for b in button_positions:
            x = self.offset[0]+ b[0]*self.x_scale/0.8 + self.total_offset[0]
            y = self.offset[1]+ b[1]*self.y_scale/0.8 + self.total_offset[1]
            if x < min_x:
                min_x = x
            if x > window_size.width():
                new_max = x - window_size.width()
                if new_max > max_x:
                    max_x = new_max
            if y < min_y:
                min_y = y
            if y > window_size.height():
                new_max = y - window_size.height()
                if new_max > max_y:
                    max_y = new_max
        if min_x != 0:
            self.offset = (self.offset[0]-min_x, self.offset[1])
        if max_x != 0:
            self.offset = (self.offset[0]-max_x, self.offset[1])
        if min_y != 0:
            self.offset = (self.offset[0], self.offset[1]-min_y)
        if max_y != 0:
            self.offset = (self.offset[0], self.offset[1]-max_y)
    
    @staticmethod
    def add_function(name, pixmap, function, function_name):
        ContextMenu.function_list[name] = (pixmap, function, function_name)
    
    def mousePressEvent(self, event):
        button = event.button()
        super().mousePressEvent(event)
        self.hide()
    
    def add_buttons(self, buttons):
        """
        Add buttons to the context menu
        """
        total_offset = self.total_offset
        for b in buttons:
            function_info = b[0]
            button_position = b[1]
            button_number = button_position[2]
            button = self.ContextButton(
                self, 
                self.main_form, 
                input_pixmap=function_info[0], 
                input_function=function_info[1], 
                input_function_text=function_info[2],
                input_focus_last_widget=data.HexButtonFocus.TAB,
                input_scale=(self.x_scale, self.y_scale),
            )
            button.number = button_number
            #Set the button size and location
            button.set_offset(
                (self.offset[0]+ button_position[0]*self.x_scale/0.8 + total_offset[0], 
                    self.offset[1]+ button_position[1]*self.y_scale/0.8 + total_offset[1])
            )
            button.dim()
            self.button_list.append(button)
    
    def create_horizontal_multiline_repl_buttons(self):
        # Check if any of the buttons are out of the window and adjust the offset
        self.check_position_offset(
            inner_buttons=False, 
            outer_buttons=False,
            horizontal_buttons=True
        )
        buttons = [ContextMenu.horizontal_buttons[x] for x in range(19, 26)]
        # Add the buttons
        self.button_list = []
        self.add_horizontal_buttons(buttons)
        self.functions_type = "horizontal"
    
    def create_multiline_repl_buttons(self):
        inner_buttons = [ContextMenu.horizontal_buttons[x] for x in range(19, 26)]
        self.create_buttons(inner_buttons)
        self.functions_type = "horizontal"
    
    def create_plain_buttons(self):
        inner_buttons = [ContextMenu.standard_buttons[x] for x in range(7)]
        self.create_buttons(inner_buttons)
        self.functions_type = "plain"
    
    def create_standard_buttons(self):
        inner_buttons = [ContextMenu.standard_buttons[x] for x in range(7)]
        outer_buttons = [ContextMenu.standard_buttons[x] for x in range(7, len(ContextMenu.standard_buttons))]
        self.create_buttons(inner_buttons, outer_buttons)
        self.functions_type = "standard"
    
    def create_special_buttons(self):
        inner_buttons = [ContextMenu.special_buttons[x] for x in range(7)]
        outer_buttons = [ContextMenu.special_buttons[x] for x in range(7, len(ContextMenu.standard_buttons))]
        self.create_buttons(inner_buttons, outer_buttons)
        self.functions_type = "special"
    
    def create_buttons(self, 
                       inner_buttons=[], 
                       outer_buttons=[]):
        # Check if any of the buttons are out of the window and adjust the offset
        if outer_buttons == []:
            self.check_position_offset(
                inner_buttons=True, 
                outer_buttons=False,
                horizontal_buttons=False
            )
        else:
            self.check_position_offset()
        # Add the buttons
        self.button_list = []
        if inner_buttons != []:
            buttons = inner_buttons
            self.add_inner_buttons(buttons)
        if outer_buttons != []:
            buttons = outer_buttons
            self.add_outer_buttons(outer_buttons)
    
    def add_inner_buttons(self, in_buttons):
        self._add_buttons(in_buttons, 7, ContextMenu.inner_button_positions)
    
    def add_outer_buttons(self, in_buttons):
        self._add_buttons(in_buttons, 12, ContextMenu.outer_button_positions)
    
    def add_horizontal_buttons(self, in_buttons):
        self._add_buttons(in_buttons, 7, ContextMenu.horizontal_button_positions)
    
    def _add_buttons(self, in_buttons, max_count, positions):
        if len(in_buttons) > max_count:
            raise Exception("Too many inner buttons in context menu!")
        buttons = []
        for i,button in enumerate(in_buttons):
            if (button in self.function_list) == False:
                self.main_form.display.repl_display_message(
                    "'{}' context menu function does not exist!".format(button), 
                    message_type=data.MessageType.ERROR
                )
            else:
                buttons.append(
                    (ContextMenu.function_list[button], positions[i])
                )
        self.add_buttons(buttons)
    
    def show(self):
        super().show()
        # When the context menu is shown it is needed to paint
        # the background or the backgrounds will be transparent
        for button in self.button_list:
            button.setVisible(True)
            button._fill_background_color()



"""
---------------------------------------------------------
Custom Yes/No dialog window
---------------------------------------------------------
""" 
class YesNoDialog(data.QDialog):
    class Button(data.QLabel):
        pixmap = None
        text = None
        return_code = None
        scale = 1.0
        
        on_signal = data.PyQt.QtCore.pyqtSignal()
        off_signal = data.PyQt.QtCore.pyqtSignal()
        
        def __init__(self, parent, image, text, return_code, scale=1.0):
            # Initialize superclass
            super().__init__(parent)
            # Set the on/off images
            self.pixmap = data.PyQt.QtGui.QPixmap(image)
            self.scale = scale
            if scale != 1.0:
                self.pixmap = self.pixmap.scaled(
                    self.pixmap.size() * scale, 
                    transformMode=data.PyQt.QtCore.Qt.SmoothTransformation
                )
            # Set the text and return code
            self.text = text
            self.return_code = return_code
            # Enable mouse move events
            self.setMouseTracking(True)
            self.setScaledContents(True)
            # Disable the button on startup
            self.off()
        
        def draw(self, opacity):
            image = data.PyQt.QtGui.QImage(
                self.pixmap.size(),
                data.PyQt.QtGui.QImage.Format_ARGB32_Premultiplied
            )
            image.fill(data.PyQt.QtCore.Qt.transparent)
            painter = data.PyQt.QtGui.QPainter(image)
            painter.setOpacity(opacity)
            painter.drawPixmap(0, 0, self.pixmap)
            
            if opacity < 0.5:
                painter.setPen(data.PyQt.QtGui.QColor(0, 0, 0))
            else:
                painter.setPen(data.PyQt.QtGui.QColor(255, 255, 255))
            painter.setFont(
                data.PyQt.QtGui.QFont(
                    'Segoe UI', 16*self.scale, data.PyQt.QtGui.QFont.Bold
                )
            )
            painter.setOpacity(1.0)
            painter.drawText(
                self.pixmap.rect(), data.PyQt.QtCore.Qt.AlignCenter, self.text
            )
            painter.end()
            # Display the manipulated image
            self.setPixmap(data.PyQt.QtGui.QPixmap.fromImage(image))
            # Set the button mask, which sets the button area to the shape of
            # the button image instead of a rectangle
            self.setMask(self.pixmap.mask())
        
        def on(self):
            self.draw(1.0)
        
        def off(self):
            self.draw(0.0)
        
        def mouseMoveEvent(self, event):
            super().mouseMoveEvent(event)
            # Show the button
            self.on()
            self.on_signal.emit()
        
        def enterEvent(self, event):
            super().enterEvent(event)
            # Bring the widget to the front of the Z-axis stack
            self.raise_()
            # Show the button
            self.on()
            self.on_signal.emit()
        
        def leaveEvent(self, event):
            super().leaveEvent(event)
            # Hide the button
            self.off()
            self.off_signal.emit()
        
        def mousePressEvent(self, event):
            #Execute the superclass mouse click event first
            super().mousePressEvent(event)
            self.parent().done(self.return_code)
    
    state = False
    scale = 1.0
    
    def __init__(self, text, dialog_type=None):
        super().__init__()
        # Make the dialog stay on top
        self.setWindowFlags(data.PyQt.QtCore.Qt.WindowStaysOnTopHint)
        # Setup the image
        original_dialog_image = data.PyQt.QtGui.QPixmap(
            os.path.join(
                data.application_directory,
                data.resources_directory, 
                "various/dialog-yes-no.png"
            )
        )
        dialog_image = original_dialog_image.scaled(
            original_dialog_image.size() * self.scale,
            transformMode=data.PyQt.QtCore.Qt.SmoothTransformation
        )
        self.image = data.QLabel(self)
        self.image.setPixmap(dialog_image)
        self.image.setGeometry(
            0,
            0,
            dialog_image.rect().width() * self.scale,
            dialog_image.rect().height() * self.scale,
        )
        self.image.setScaledContents(True)
        # Set the dialog mask to match the image mask
        self.setMask(dialog_image.mask())
        # Setup the image behind the label
        if dialog_type != None:
            if dialog_type == "question":
                type_pixmap = data.PyQt.QtGui.QPixmap(
                    os.path.join(
                        data.resources_directory,
                        "various/dialog-question.png"
                    )
                )
            elif dialog_type == "warning":
                type_pixmap = data.PyQt.QtGui.QPixmap(
                    os.path.join(
                        data.resources_directory,
                        "various/dialog-warning.png"
                    )
                )
            elif dialog_type == "error":
                type_pixmap = data.PyQt.QtGui.QPixmap(
                    os.path.join(
                        data.resources_directory,
                        "various/dialog-error.png"
                    )
                )
            else:
                raise Exception("Wrong dialog type!")
            image = data.PyQt.QtGui.QImage(
                type_pixmap.size(),
                data.PyQt.QtGui.QImage.Format_ARGB32_Premultiplied
            )
            image.fill(data.PyQt.QtCore.Qt.transparent)
            painter = data.PyQt.QtGui.QPainter(image)
            painter.setOpacity(0.2)
            painter.drawPixmap(0, 0, type_pixmap)
            painter.end()
            type_pixmap = data.PyQt.QtGui.QPixmap.fromImage(image)
            type_pixmap = type_pixmap.scaled(
                type_pixmap.size() * 2.0 * self.scale, 
                transformMode=data.PyQt.QtCore.Qt.SmoothTransformation
            )
            self.type_label = data.QLabel(self)
            self.type_label.setPixmap(type_pixmap)
            type_label_rect = data.PyQt.QtCore.QRect(
                (self.image.rect().width() - type_pixmap.rect().width())/2 * self.scale,
                (self.image.rect().height() - type_pixmap.rect().height())/2 * self.scale,
                type_pixmap.rect().width() * self.scale,
                type_pixmap.rect().height() * self.scale,
            )
            self.type_label.setGeometry(type_label_rect)
        # Setup the text label
        self.text = text
        self.label = data.QLabel(self)
        self.label.setFont(
            data.PyQt.QtGui.QFont(
                'Segoe UI', 12 * self.scale, data.PyQt.QtGui.QFont.Bold
            )
        )
        self.label.setWordWrap(True)
        self.label.setAlignment(data.PyQt.QtCore.Qt.AlignCenter)
        self.label.setText(text)
        width_diff = self.image.rect().width() - original_dialog_image.width()
        height_diff = self.image.rect().height() - original_dialog_image.height()
        x_offset = 20 * (self.scale - 1.0)
        y_offset = 60 * (self.scale - 1.0)
        label_rect = data.PyQt.QtCore.QRect(
            dialog_image.rect().x() + 20 + x_offset,
            dialog_image.rect().y() + 60 + y_offset,
            dialog_image.rect().width() - (40 * self.scale),
            dialog_image.rect().height() - (120* self.scale),
        )
        self.label.setGeometry(label_rect)
        # Shrink text if needed
        for i in range(10):
            label_width = label_rect.width()
            label_height = label_rect.height()
            font_metrics = data.PyQt.QtGui.QFontMetrics(self.label.font())
            bounding_rectangle = font_metrics.boundingRect(
                data.PyQt.QtCore.QRect(0, 0, label_width, label_height),
                self.label.alignment() | data.PyQt.QtCore.Qt.TextWordWrap,
                text
            )
            if (bounding_rectangle.width() > label_width or 
                bounding_rectangle.height() > label_height):
                self.label.setFont(
                    data.PyQt.QtGui.QFont(
                        'Segoe UI', (12-i) * self.scale, data.PyQt.QtGui.QFont.Bold
                    )
                )
            else:
                break
        # Setup the buttons
        self.button_yes = self.Button(
            self, 
            os.path.join(
                data.resources_directory,
                "various/hex-green.png"
            ),
            "Yes", 
            data.QMessageBox.Yes, 
            self.scale
        )
        x_offset = 93 * (self.scale - 1.0)
        y_offset = 3 * (self.scale - 1.0)
        self.button_yes.setGeometry(
            93+x_offset,
            3+y_offset,
            59 * self.scale,
            50 * self.scale
        )
        self.button_yes.on_signal.connect(self.update_state_on)
        self.button_yes.off_signal.connect(self.update_state_reset)
        self.button_no = self.Button(
            self, 
            os.path.join(
                data.resources_directory,
                "various/hex-red.png"
            ),
            "No", 
            data.QMessageBox.No, 
            self.scale
        )
        x_offset = 93 * (self.scale - 1.0)
        y_offset = 158 * (self.scale - 1.0)
        self.button_no.setGeometry(
            93+x_offset,
            158+y_offset,
            59 * self.scale,
            50 * self.scale
        )
        self.button_no.on_signal.connect(self.update_state_off)
        self.button_no.off_signal.connect(self.update_state_reset)
        # Setup the layout
        self.layout = data.QGridLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(data.PyQt.QtCore.QMargins(0,0,0,0))
        self.layout.addWidget(self.image)
        self.setLayout(self.layout)
        # Setup tranparency and borders
        self.image.setAttribute(data.PyQt.QtCore.Qt.WA_TranslucentBackground)
        self.image.setStyleSheet(
            "border:0;" +
            "background-color:transparent;"
        )
        self.setAttribute(data.PyQt.QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet(
            "border:0;" +
            "background-color:transparent;"
        )
        
        self.setGeometry(dialog_image.rect())
        self.center()
        self.setWindowFlags(data.PyQt.QtCore.Qt.FramelessWindowHint)
    
    def update_state_on(self):
        self.state = True
        self.button_no.off()
    
    def update_state_off(self):
        self.state = False
        self.button_yes.off()
    
    def update_state_reset(self):
        self.state = None
    
    def state_on(self):
        self.state = True
        self.button_no.off()
        self.button_yes.on()
    
    def state_off(self):
        self.state = False
        self.button_no.on()
        self.button_yes.off()
    
    def state_reset(self):
        self.state = None
        self.button_no.off()
        self.button_yes.off()
    
    def center(self):
        qr = self.frameGeometry()
        cp = data.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    
    def keyPressEvent(self, key_event):
        pressed_key = key_event.key()
        #Check for escape keypress
        if pressed_key == data.PyQt.QtCore.Qt.Key_Escape:
            self.button_no.on()
            self.repaint()
            time.sleep(0.1)
            self.done(data.QMessageBox.No)
        elif pressed_key == data.PyQt.QtCore.Qt.Key_Down:
            self.state_off()
        elif pressed_key == data.PyQt.QtCore.Qt.Key_Up:
            self.state_on()
        elif pressed_key == data.PyQt.QtCore.Qt.Key_Enter or pressed_key == data.PyQt.QtCore.Qt.Key_Return:
            if self.state == True:
                self.done(data.QMessageBox.Yes)
            elif self.state == False:
                self.done(data.QMessageBox.No)
    
    @staticmethod
    def blank(text):
        return YesNoDialog(text).exec_()
    
    @staticmethod
    def question(text):
        return YesNoDialog(text, "question").exec_()
    
    @staticmethod
    def warning(text):
        return YesNoDialog(text, "warning").exec_()
    
    @staticmethod
    def error(text):
        return YesNoDialog(text, "error").exec_()
    
    
    
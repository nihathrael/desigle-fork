#    DeSiGLE
#    Origninal Copyright (C) 2008 Derek Anderson
#    Changes Copyright (C) 2010 Greg McWhirter
#    Changes Copyright (C) 2010 Thomas Kinnen
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import pygtk
pygtk.require("2.0")
import gobject
import gtkspell
import gtk
import gtk.glade
import gnome
import gnome.ui
import pango
import gconf
import poppler
import config
import time
import traceback
import subprocess
import tempfile
import thread
from datetime import datetime

from latex_tags import *
from texdocument import TexDocument
from prefgui import PrefGUI
from util import pango_escape

class MainGUI:

    config = config.GConfConfig('/apps/desigle')

    tex_docs = []
    errors = []
    recent_files = []
    refresh_pdf_preview = False

    def get_current_tex_doc(self):
        current_page = self.notebook.get_current_page()
        if current_page<0:
            return None
        else:
            return self.tex_docs[current_page]

    def handle_notebook_switch_page_event(self, x, y, page_num):
        #print 'handle_notebook_select_page_event', x, y, page_num
        self.refresh_pdf_preview = True
        if len(self.tex_docs)<=page_num: return
        current_tex_doc = self.tex_docs[page_num]
        if not current_tex_doc: return
        self.ui.get_widget('menu_undo').set_sensitive(current_tex_doc.text_buffer.can_undo())
        self.ui.get_widget('menu_redo').set_sensitive(False)
        self.ui.get_widget('menu_save').set_sensitive( current_tex_doc.changed or not current_tex_doc.fq_filename )
        self.ui.get_widget('toolbutton_save').set_sensitive( current_tex_doc.changed or not current_tex_doc.fq_filename )

    def __init__(self):
        gnome.init(config.PROGRAM, config.VERSION)
        self.ui = gtk.glade.XML(RUN_FROM_DIR + 'desigle.glade')
        self.main_window = self.ui.get_widget('desigle')
        self.notebook = self.ui.get_widget('notebook_editor')
        self.main_window.connect("delete-event", lambda x,y: self.exit() )

        self.init_menu()
        self.init_editor()
        self.init_editor_errors()
        self.init_pdf_preview_pane()
        self.init_toolbar_find()

        thread.start_new_thread( self.watch_editor, () )

        self.main_window.show()

    def init_editor(self):
        pangoFont = pango.FontDescription('monospace')
        self.ui.get_widget('textview_output').modify_font(pangoFont)

        self.notebook.set_scrollable(True)
        self.notebook.connect('switch-page', self.handle_notebook_switch_page_event )

        # undo/redo
        accelgroup = gtk.AccelGroup()
        actiongroup = gtk.ActionGroup('SimpleAction')
        self.main_window.add_accel_group(accelgroup)
        undo_action = gtk.Action('undo_action', None, None, gtk.STOCK_UNDO)
        undo_action.connect('activate', lambda x: self.editor_undo())
        actiongroup.add_action_with_accel(undo_action, '<Control>z')
        undo_action.set_accel_group(accelgroup)
        undo_action.connect_accelerator()
        undo_action.connect_proxy(self.ui.get_widget('menu_undo'))
        redo_action = gtk.Action('redo_action', None, None, gtk.STOCK_REDO)
        redo_action.connect('activate', lambda x: self.editor_redo())
        actiongroup.add_action_with_accel(redo_action, '<Control>y')
        redo_action.set_accel_group(accelgroup)
        redo_action.connect_accelerator()
        redo_action.connect_proxy(self.ui.get_widget('menu_redo'))
        self.ui.get_widget('menu_undo').set_sensitive(False)
        self.ui.get_widget('menu_redo').set_sensitive(False)


    def init_menu(self):
        self.ui.get_widget('menu_new').connect('activate', lambda x: self.new())
        self.ui.get_widget('menu_open').connect('activate', lambda x: self.open())
        self.ui.get_widget('menu_save').connect('activate', lambda x: self.save())
        self.ui.get_widget('menu_save_as').connect('activate', lambda x: self.save_as())
        self.ui.get_widget('menu_quit').connect('activate', lambda x: self.exit())
        self.ui.get_widget('menu_about').connect('activate', self.show_about_dialog )
        self.ui.get_widget('menu_check_updates').connect('activate', lambda x: self.check_for_updates() )
        self.ui.get_widget('menu_find').connect('activate', lambda x: self.toggle_find())
        self.ui.get_widget('menuitem_preferences').connect('activate', lambda x: PrefGUI())

        self.ui.get_widget('menu_save').set_sensitive( False )

        self.ui.get_widget('toolbutton_new').connect('clicked', lambda x: self.new())
        self.ui.get_widget('toolbutton_open').connect('clicked', lambda x: self.open())
        self.ui.get_widget('toolbutton_save').connect('clicked', lambda x: self.save())
        self.ui.get_widget('toolbutton_save').set_sensitive( False )

        menuitem_recent_files = self.ui.get_widget('menuitem_recent_files')
        self.recent_files = self.config.get_list('recent_files')
        if not self.recent_files: self.recent_files = []
        menu = gtk.Menu()
        for recent_file in self.recent_files:
            menu_item = gtk.MenuItem(label=recent_file)
            menu_item.connect( 'activate', lambda x,recent_file: self.open_file(recent_file), recent_file )
            menu.append(menu_item)
        menu.show_all()
        menuitem_recent_files.set_submenu(menu)



    def init_toolbar_find(self):
        toolbar_find = self.ui.get_widget('toolbar_find')
        toolbar_find.set_property('visible', False)
        self.ui.get_widget('toolbutton_find_cancel').connect('clicked', lambda x: self.toggle_find())
        self.ui.get_widget('entry_find').connect('changed', self.entry_find_changed_event )
        self.ui.get_widget('toolbutton_find_forward').connect('clicked', lambda x: self.find_forward())
        self.ui.get_widget('toolbutton_find_backward').connect('clicked', lambda x: self.find_backward())




    def init_editor_errors(self):
        self.treeview_errors = self.ui.get_widget('treeview_errors')
        # icon, line_number, error
        self.treeview_errors_model = gtk.ListStore( gtk.gdk.Pixbuf, str, int, str )
        self.treeview_errors.set_model( self.treeview_errors_model )

        column = gtk.TreeViewColumn()
        self.treeview_errors.append_column(column)
        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, expand=False)
        column.add_attribute(renderer, 'pixbuf', 0)
        #self.treeview_errors.append_column( gtk.TreeViewColumn("", gtk.CellRendererText(), text=1) )
        self.treeview_errors.append_column( gtk.TreeViewColumn("", gtk.CellRendererText(), text=2) )
        self.treeview_errors.append_column( gtk.TreeViewColumn("", gtk.CellRendererText(), text=3) )

        self.treeview_errors.get_selection().connect('changed', self.handle_errors_selection_changed )


    def handle_errors_selection_changed(self, selection):
        liststore, iter = selection.get_selected()
        if not iter: return
        file_name = liststore[iter][1]
        line_number = liststore[iter][2]
        if file_name == self.tex_file:
            editor = self.get_current_tex_doc().editor
        else:
            return # TODO: select the right notebook tab
        buffer = editor.get_buffer()
        found_iter = buffer.get_iter_at_line(line_number)
        editor.scroll_to_iter( found_iter, 0.1 )



    def toggle_find(self):
        toolbar_find = self.ui.get_widget('toolbar_find')
        if toolbar_find.get_property('visible'):
            toolbar_find.set_property('visible', False)
            self.editor.grab_focus()
            buffer = self.editor.get_buffer()
            buffer.remove_tag_by_name('search_highlight', buffer.get_start_iter(), buffer.get_end_iter())
        else:
            entry_find = self.ui.get_widget('entry_find')
            entry_find.set_text('')
            toolbar_find.set_property('visible', True)
            entry_find.grab_focus()


    def entry_find_changed_event(self, entry_find):
        search_text = entry_find.get_text()
        self.find_forward(search_text)


    def editor_undo(self):
        buffer = self.get_current_tex_doc().text_buffer
        if buffer.can_undo():
            buffer.undo()
        self.ui.get_widget('menu_undo').set_sensitive(buffer.can_undo())


    def editor_redo(self):
        buffer = self.get_current_tex_doc().text_buffer
        if buffer.can_redo():
            buffer.redo()
        self.ui.get_widget('menu_redo').set_sensitive(buffer.can_redo())

    def init_pdf_preview_pane(self):
        file, self.tex_file = tempfile.mkstemp('.tex')
        self.pdf_file = self.tex_file[:-4]+'.pdf'
        #print 'tex_file', self.tex_file
        #print 'pdf_file', self.pdf_file

        pdf_preview = self.ui.get_widget('pdf_preview')
        self.pdf_preview = { 'current_page_number':0 }
        self.pdf_preview['scale'] = None
        pdf_preview.connect("expose-event", self.on_expose_pdf_preview)

        self.ui.get_widget('button_move_previous_page').connect('clicked', lambda x: self.goto_pdf_page( self.pdf_preview['current_page_number']-1 ) )
        self.ui.get_widget('button_move_next_page').connect('clicked', lambda x: self.goto_pdf_page( self.pdf_preview['current_page_number']+1 ) )
        self.ui.get_widget('button_zoom_in').connect('clicked', lambda x: self.zoom_pdf_page( -1.2 ) )
        self.ui.get_widget('button_zoom_out').connect('clicked', lambda x: self.zoom_pdf_page( -.8 ) )
        self.ui.get_widget('button_zoom_normal').connect('clicked', lambda x: self.zoom_pdf_page( 1 ) )
        self.ui.get_widget('button_zoom_best_fit').connect('clicked', lambda x: self.zoom_pdf_page( None ) )

    def refresh_pdf_preview_pane(self):
        pdf_preview = self.ui.get_widget('pdf_preview')
        rebuild = False

        if os.path.isfile( self.pdf_file ):
            try:
                self.pdf_preview['document'] = poppler.document_new_from_file ('file://%s' % (self.pdf_file), None)
                self.pdf_preview['n_pages'] = self.pdf_preview['document'].get_n_pages()
                self.pdf_preview['scale'] = None
                self.goto_pdf_page( self.pdf_preview['current_page_number'], new_doc=True )
            except glib.GError:
                rebuild = True
        else:
            rebuild = True

        if rebuild:
            pdf_preview.set_size_request(0,0)
            self.pdf_preview['current_page'] = None
            self.ui.get_widget('button_move_previous_page').set_sensitive( False )
            self.ui.get_widget('button_move_next_page').set_sensitive( False )
            self.ui.get_widget('button_zoom_out').set_sensitive( False )
            self.ui.get_widget('button_zoom_in').set_sensitive( False )
            self.ui.get_widget('button_zoom_normal').set_sensitive( False )
            self.ui.get_widget('button_zoom_best_fit').set_sensitive( False )
        pdf_preview.queue_draw()

    def goto_pdf_page(self, page_number, new_doc=False):
        if True:
            if not new_doc and self.pdf_preview.get('current_page') and self.pdf_preview['current_page_number']==page_number:
                return
            if page_number<0: page_number = 0
            pdf_preview = self.ui.get_widget('pdf_preview')
            self.pdf_preview['current_page_number'] = page_number
            self.pdf_preview['current_page'] = self.pdf_preview['document'].get_page( self.pdf_preview['current_page_number'] )
            if self.pdf_preview['current_page']:
                self.pdf_preview['width'], self.pdf_preview['height'] = self.pdf_preview['current_page'].get_size()
                self.ui.get_widget('button_move_previous_page').set_sensitive( page_number>0 )
                self.ui.get_widget('button_move_next_page').set_sensitive( page_number<self.pdf_preview['n_pages']-1 )
                self.zoom_pdf_page( self.pdf_preview['scale'], redraw=False )
            else:
                self.ui.get_widget('button_move_previous_page').set_sensitive( False )
                self.ui.get_widget('button_move_next_page').set_sensitive( False )
            pdf_preview.queue_draw()
        else:
            self.ui.get_widget('button_move_previous_page').set_sensitive( False )
            self.ui.get_widget('button_move_next_page').set_sensitive( False )

    def zoom_pdf_page(self, scale, redraw=True):
        """None==auto-size, negative means relative, positive means fixed"""
        if True:
            if redraw and self.pdf_preview.get('current_page') and self.pdf_preview['scale']==scale:
                return
            pdf_preview = self.ui.get_widget('pdf_preview')
            auto_scale = (pdf_preview.get_parent().get_allocation().width-2.0) / self.pdf_preview['width']
            if scale==None:
                scale = auto_scale
            else:
                if scale<0:
                    if self.pdf_preview['scale']==None: self.pdf_preview['scale'] = auto_scale
                    scale = self.pdf_preview['scale'] = self.pdf_preview['scale'] * -scale
                else:
                    self.pdf_preview['scale'] = scale
            pdf_preview.set_size_request(int(self.pdf_preview['width']*scale), int(self.pdf_preview['height']*scale))
            self.ui.get_widget('button_zoom_out').set_sensitive( scale>0.3 )
            self.ui.get_widget('button_zoom_in').set_sensitive( True )
            self.ui.get_widget('button_zoom_normal').set_sensitive( True )
            self.ui.get_widget('button_zoom_best_fit').set_sensitive( True )
            if redraw: pdf_preview.queue_draw()
            return scale
        else:
            pass

    def on_expose_pdf_preview(self, widget, event):
        if not self.pdf_preview.get('current_page'): return
        cr = widget.window.cairo_create()
        cr.set_source_rgb(1, 1, 1)
        scale = self.pdf_preview['scale']
        if scale==None:
            scale = (self.ui.get_widget('pdf_preview').get_parent().get_allocation().width-2.0) / self.pdf_preview['width']
        if scale != 1:
            cr.scale(scale, scale)
        cr.rectangle(0, 0, self.pdf_preview['width'], self.pdf_preview['height'])
        cr.fill()
        self.pdf_preview['current_page'].render(cr)


    def highlight_errors(self, output):
        self.errors = []
        p = re.compile('(.+):([0-9]+):(.*)')
        for line in output.split('\n'):
            if line.startswith('! LaTeX Error:'):
                self.errors.append( ( 'LaTeX Error', 0, line ) )
            for match in p.finditer(line):
                error_line = self.error_line_offset + int(match.group(2))
                self.errors.append( ( match.group(1), error_line, match.group(3) ) )

        try:
            self.treeview_errors_model.clear()
            self.treeview_errors.set_property('visible', bool(self.errors) )
            for error in self.errors:
                self.treeview_errors_model.append( (self.get_current_tex_doc().editor.render_icon(gtk.STOCK_CANCEL, gtk.ICON_SIZE_MENU), error[0], error[1], error[2]) )
        except:
            traceback.print_exc()


    def refresh_preview(self):
        if os.path.isfile( self.pdf_file ): os.remove( self.pdf_file )

        if not self.tex_docs: return
        text_buffer = self.get_current_tex_doc().editor.get_buffer()
        tex = text_buffer.get_text( text_buffer.get_start_iter(), text_buffer.get_end_iter() )
        if self.config.get_bool( 'pref_auto_add_doc_tags_in_preview') and tex.find('\\documentclass')==-1:
            tex = '\\documentclass{%s}\n\\begin{document}\n' % self.config.get_string( 'default_doc_class', default='article' ) \
                + tex + '\n\\end{document}\n'
            self.error_line_offset = -2
        else:
            self.error_line_offset = 0
        ftex = open( self.tex_file, 'w' )
        ftex.write( tex )
        ftex.close()

        os.chdir('/tmp')
        #child_stdin, child_stdout = os.popen2( 'pdflatex -file-line-error -src-specials -halt-on-error "%s"' % (self.tex_file) )
        if self.get_current_tex_doc().fq_filename:
            fdir = os.path.realpath(os.path.dirname(self.get_current_tex_doc().fq_filename))
            cmd_string = 'rubber -s -I "%s" -d -c \'bibtex.path "%s"\' -c \'bibtex.stylepath "%s"\' -c \'index.path "%s"\' -v "%s"' % (fdir,fdir,fdir,fdir,self.tex_file)
            #cmd_string = 'TEXINPUTS=%s: pdflatex -file-line-error -src-specials -halt-on-error "%s"' % (os.path.dirname(self.get_current_tex_doc().fq_filename),self.tex_file)
        else:
            cmd_string = 'rubber -s -d -v "%s"' % (self.tex_file)
            #cmd_string = 'pdflatex -file-line-error -src-specials -halt-on-error "%s"' % (self.tex_file)
        #print cmd_string
        p = subprocess.Popen(cmd_string, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        (child_stdin, child_stdout) = (p.stdin, p.stdout)
        child_stdin.close()
        output = child_stdout.read()
        child_stdout.close()
        os.chdir(config.CURRENT_DIR)
        self.ui.get_widget('textview_output').get_buffer().set_text(output)

        self.highlight_errors(output)

        self.refresh_pdf_preview_pane()
        self.get_current_tex_doc().changed_time = None
        self.refresh_pdf_preview = False

    def exit(self):

        for tex_doc in list(self.tex_docs):
            if tex_doc.close():
                return True

        if len(self.recent_files)>10:
            self.recent_files = self.recent_files[:10]
        self.config.set_list('recent_files', self.recent_files)

        if os.path.isfile( self.tex_file ): os.remove( self.tex_file )
        if os.path.isfile( self.pdf_file ): os.remove( self.pdf_file )
        sys.exit(0)


    def new(self):
        self.tex_docs.append( TexDocument(self) )


    def open(self):
        os.chdir(config.CURRENT_DIR)
        dialog = gtk.FileChooserDialog(title='Select a TEX file...', parent=None, action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK), backend=None)
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            config.CURRENT_DIR = dialog.get_current_folder()
            filename = dialog.get_filename()
            self.open_file( filename )
        dialog.destroy()


    def open_file(self, filename):
        if not os.path.isfile(filename):
            self.new()
            return
        filename = os.path.abspath(filename)
        self.tex_docs.append( TexDocument(self, filename) )

        while filename in self.recent_files:
            self.recent_files.remove(filename)
        self.recent_files.insert(0,filename)

        self.refresh_preview()



    def save_as(self):
        return self.get_current_tex_doc().save_as()

    def save(self):
        return self.get_current_tex_doc().save()


    def check_for_autocomplete_patterns(self):
        try:
            recommendations = []
            text_buffer = self.get_current_tex_doc().editor.get_buffer()
            here = text_buffer.get_iter_at_mark( text_buffer.get_insert() )
            before = text_buffer.get_text( text_buffer.get_iter_at_line(here.get_line()), here )
            after = text_buffer.get_text( here, text_buffer.get_iter_at_line_offset(here.get_line(),max(0,here.get_chars_in_line()-1)) )
            for s in AUTOCOMPLETE_PLUS:
                for i in range(1,len(s)):
                    if before.endswith( s[:i] ):
                        if not after.startswith( s[i:i+3] ):
                            recommendations.append((i,s))
                            break
            if recommendations:
                #self.show_recommendations(recommendations)
                self.get_current_tex_doc().changed_time = None
                return False
        except:
            traceback.print_exc()

    def recommendation_menu_key_press_event(self, menu, event):
        if event.keyval in [65288, 65535]:
            menu.destroy()
        if event.string and event.keyval<256:
            self.get_current_tex_doc().editor.get_buffer().insert_at_cursor(event.string)
            menu.destroy()

    def show_recommendations(self, recommendations):
        x,y = self.get_current_tex_doc().get_actual_screen_coords_of_text_cursor()
        menu = gtk.Menu()
        menu.connect('key-press-event', self.recommendation_menu_key_press_event)
        for i,s in recommendations:
            menu_item = gtk.MenuItem(label=s.replace('\n','...'))
            menu_item.connect( 'activate', lambda x,i,s: self.get_current_tex_doc().editor.get_buffer().insert_at_cursor(s[i:]), i, s )
            menu.append(menu_item)
        menu.show_all()
        menu.popup(None, None, None, 0, 0)
        menu.get_parent_window().move( x, y )


    def watch_editor(self):
        while True:
            try:
                if self.tex_docs and (self.refresh_pdf_preview or (self.get_current_tex_doc() and self.get_current_tex_doc().changed_time and (datetime.now() - self.get_current_tex_doc().changed_time).seconds >= 1)):
                    gtk.gdk.threads_enter()
                    if not self.check_for_autocomplete_patterns():
                        self.refresh_preview()
                        self.get_current_tex_doc().retag()
                    gtk.gdk.threads_leave()
            except:
                traceback.print_exc()
            time.sleep(.5)


    def check_for_updates(self):
        parent_self = self
        class UpdateThread(threading.Thread):
            def run(self):
                os.chdir(RUN_FROM_DIR)
                output = commands.getoutput('svn update')
                gtk.gdk.threads_enter()
                dialog = gtk.MessageDialog( type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK )
                dialog.connect('response', lambda x,y: dialog.destroy())
                dialog.set_markup('<b>Output from SVN:</b>\n\n%s\n\n(restart for changes to take effect)' % ( pango_escape(output) ))
                dialog.show_all()
                response = dialog.run()
                gtk.gdk.threads_leave()
        t = UpdateThread()
        t.start()


    def show_about_dialog(self, o):
        about = gtk.AboutDialog()
        about.set_name(PROGRAM)
        about.set_version(VERSION)
        about.set_copyright('Original Copyright (c) 2008 Derek Anderson\nChanges Copyright (c) 2010 Greg McWhirter')
        about.set_comments('''Derek's Simple Gnome LaTeX Editor''')
        about.set_license(GPL)
        about.set_website('http://github.com/gsmcwhirter/desigle-fork')
        about.set_authors(['Derek Anderson: http://kered.org','Greg McWhirter: http://github.com/gsmcwhirter/'])
        about.connect('response', lambda x,y: about.destroy())
        about.show()

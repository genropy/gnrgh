# -*- coding: utf-8 -*-

# gnride.py - Dark theme override for Sourcerer
# Based on gnrcomponents/gnride/gnride from GenroPy framework
import os
import sys

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag, DirectoryResolver
from gnr.core.gnrconfig import getGenroRoot

DIRECTORY_RESOLVER_DEFAULT_PARS = {
    'include': '*.py,*.js,*.xml,*.html,*.css',
    'processors': {'xml': False},
    'exclude': '_*,.*',
    'dropext': True,
    'readOnly': False,
    'cacheTime': 10
}

DARK_BG = '#1e1e1e'
DARK_PANEL = '#252526'
DARK_TOOLBAR = '#333333'
DARK_BORDER = '#444444'
DARK_TEXT = '#cccccc'
DARK_TEXT_DIM = '#999999'


class GnrIdeDark(BaseComponent):
    css_requires = 'gnrcomponents/gnride/gnride'
    js_requires = 'gnrcomponents/gnride/gnride'

    @struct_method
    def gi_gnrIdeFrame(self, parent, nodeId=None, debugEnabled=False,
                       sourceFolders=None, emptyStart=False, **kwargs):
        ideId = nodeId or 'mainIDE'

        bc = parent.borderContainer(nodeId=ideId, _activeIDE=True,
                                    selfsubscribe_openModuleToEditorStack="this._gnrIdeHandler.openModuleToEditorStack($1);",
                                    selfsubscribe_debugCommand="this._gnrIdeHandler.sendCommand($1.cmd,$1.pdb_id);",
                                    onCreated="""this._gnrIdeHandler = new gnr.GnrIde(this)""",
                                    _gi_buildEditorTab=self.gi_buildEditorTab,
                                    _gi_makeEditorStack=self.gi_makeEditorStack,
                                    debugEnabled=debugEnabled, **kwargs)

        self.gi_drawerPane(bc.framePane(frameCode='%s_drawer' % ideId, region='left',
                                        width='250px', splitter=True, drawer=True,
                                        background=DARK_PANEL),
                           sourceFolders=sourceFolders, ideId=ideId,
                           emptyStart=emptyStart)
        #self.gi_dbstructPane(bc.framePane(frameCode='%s_dbstruct' % ideId, region='right',
        #                                  width='250px', splitter=True, drawer='close',
        #                                  background=DARK_PANEL))
        center = bc.framePane(frameCode=ideId, region='center')
        bar = center.top.slotToolbar('5,stackButtons,*,addIdeBtn,5',
                                      background=DARK_TOOLBAR, color=DARK_TEXT)
        bar.addIdeBtn.slotButton('Add ide',
                                  action='genro.nodeById(ideId)._gnrIdeHandler.newIde({ide_page:"ide_"+genro.getCounter(),isDebugger:true})')
        sc = center.center.stackContainer(selectedPage='^.#parent.ide_page',
                                           datapath='.instances', nodeId='%s_stack' % ideId)
        self.gi_makeEditorStack(sc.contentPane(pageName='mainEditor', title='Main Editor',
                                                overflow='hidden', datapath='.mainEditor'), 'mainEditor')
        if debugEnabled:
            bc.dataRpc('dummy', 'pdb.setBreakpoint', subscribe_setBreakpoint=True)
        return center

    @public_method
    def gi_makeEditorStack(self, pane, frameCode=None, isDebugger=False):
        bc = pane.borderContainer()
        if isDebugger:
            self.gi_debuggerPane(bc.framePane(frameCode='%s_debugger' % frameCode,
                                               height='400px', splitter=True, drawer=True, region='bottom'))
        frame = bc.framePane(frameCode=frameCode, region='center')
        slots = '5,stackButtons,*' if isDebugger else '5,stackButtons,*,readOnlySlot,5'
        bar = frame.top.slotToolbar(slots, height='20px',
                                     background=DARK_TOOLBAR, color=DARK_TEXT)
        bar.data('.readOnly', True)
        if not isDebugger:
            bar.readOnlySlot.div().checkbox(value='^.readOnly', label='Read Only')
        stackNodeId = '%s_sc' % frameCode
        frame.center.stackContainer(nodeId=stackNodeId, selectedPage='^.selectedModule')

    def gi_dbstructPane(self, frame):
        frame.data('.dbstructure', self.app.dbStructure())
        frame.top.slotToolbar('*,searchOn,2', height='20px', datapath='.dbmodel',
                               background=DARK_TOOLBAR, color=DARK_TEXT)
        pane = frame.center.contentPane(overflow='auto', background=DARK_PANEL, color=DARK_TEXT)
        pane.div(padding='10px').tree(nodeId='dbstructure_tree', storepath='.dbstructure',
                                      _class='branchtree noIcon',
                                      hideValues=True, openOnClick=True)

    def gi_drawerPane(self, frame, sourceFolders=None, ideId=None, emptyStart=False):
        bar = frame.top.slotToolbar('2,*,searchOn,2', height='20px', datapath='.dir',
                               background=DARK_TOOLBAR, color=DARK_TEXT)
        if emptyStart:
            frame.data('.directories.root', Bag(), nodecaption='!!Repositories')
        elif sourceFolders:
            frame.dataRpc('.directories.root', self.gi_sourceFoldersResolver,
                          sourceFolders=sourceFolders, nodecaption='!!Folders', _onBuilt=True,
                          _if='sourceFolders', _else='new gnr.GnrBag()')
        else:
            b = Bag()
            for k, pkgobj in list(self.application.packages.items()):
                b.setItem('projects.%s' % k,
                          DirectoryResolver(pkgobj.packageFolder, **DIRECTORY_RESOLVER_DEFAULT_PARS)(),
                          caption=pkgobj.attributes.get('name_long', k))
            b.setItem('genropy', DirectoryResolver(getGenroRoot(), **DIRECTORY_RESOLVER_DEFAULT_PARS)(),
                       caption='Genropy')
            frame.data('.directories.root', b, nodecaption='!!Folders')
        frame.dataRpc(None, self.gi_sourceFoldersResolver,
                      sourceFolders='=$1',
                      _onResoult="""
                        var dirroot = kwargs.dirroot;
                        result.forEach(function(n){
                            dirroot.setItem(n.label,n);
                        });""",
                      dirroot='=.directories.root',
                      **{'subscribe_%s_addSourceFolderRoot' % ideId: True})
        pane = frame.center.contentPane(overflow='auto', background=DARK_PANEL, color=DARK_TEXT)
        pane.div(padding='6px').tree(nodeId='drawer_tree', storepath='.directories.root', persist=True,
                                      connect_ondblclick="""var ew = dijit.getEnclosingWidget($1.target);
                                              if(ew.item && ew.item.attr.file_ext!='directory'){
                                                  this.attributeOwnerNode('_activeIDE').publish('openModuleToEditorStack',{module:ew.item.attr.abs_path});
                                              }
                                             """, _class='branchtree pdb_tree',
                                      hideValues=True, openOnClick=True, labelAttribute='nodecaption',
                                      font_size='13px')

    @public_method
    def gi_sourceFoldersResolver(self, sourceFolders=None, **kwargs):
        result = Bag()
        if not sourceFolders:
            return result
        for f in sourceFolders.split(','):
            sn = self.site.storageNode(f)
            result.setItem(sn.basename,
                           DirectoryResolver(sn.internal_path, **DIRECTORY_RESOLVER_DEFAULT_PARS),
                           caption=sn.basename)
        return result

    @public_method
    def gi_buildEditorTab(self, pane, module=None, ide_page=None, **kwargs):
        plist = module.split(os.sep)
        frameCode = '%s_%s' % (ide_page, '_'.join(plist).replace('.', '_'))
        wchunk = False
        preview_url = False
        cmroot = None
        preview_iframe = None
        frame = pane.framePane(frameCode=frameCode, region='center', _class='viewer_box selectable')
        if 'webpages' in plist:
            wchunk = 'webpages'
        if 'mobile' in plist:
            wchunk = 'mobile'
        if wchunk:
            windex = plist.index(wchunk)
            pkg = plist[windex - 1]
            if pkg not in ('sys', 'adm'):
                preview_url = '/%s' % os.path.join(pkg, *plist[windex + 1:])
                bc = frame.center.borderContainer()
                cmroot = bc.contentPane(region='center')
                rightpane = bc.contentPane(region='right', overflow='hidden', splitter=True,
                                           border_left='1px solid %s' % DARK_BORDER, background='white')
                frame.data('.preview_url', preview_url)
                preview_iframe = rightpane.iframe(src='^.preview_url', height='100%', width='100%', border=0)
                commandbar = frame.top.slotBar('5,previewButtons,10,previewReload,*,savebtn,revertbtn,5',
                                                childname='commandbar', toolbar=True,
                                                background=DARK_TOOLBAR, color=DARK_TEXT)
                commandbar.previewButtons.multiButton(value='^.sourceViewMode',
                                                       values='srconly:Source,mixed:Mixed,preview:Preview')
                commandbar.previewReload.slotButton('Reload preview',
                                                     action='SET .preview_url = preview_url+"?_nocache="+(new Date().getTime())',
                                                     hidden='^.sourceViewMode?=#v=="srconly"', preview_url=preview_url)
                bc.dataController("""var width = 0;
                            status = status || 'srconly';
                             if(status=='mixed'){
                                width = '50%';
                             }else if(status=='preview'){
                                width = '100%'
                             }
                             right.style.width = width;
                             bc.setRegionVisible('right',width!=0);
                             """,
                                  bc=bc.js_widget,
                                  status='^.sourceViewMode',
                                  right=rightpane.js_domNode, _onBuilt=True)
        else:
            commandbar = frame.top.slotBar('*,savebtn,revertbtn,5', childname='commandbar', toolbar=True,
                                            background=DARK_TOOLBAR, color=DARK_TEXT)
            cmroot = frame.center.contentPane(overflow='hidden')
        source = self._readsource(module)
        breakpoints = self.pdb.getBreakpoints(module)
        pane.data('.module', module)
        bar = frame.bottom.slotBar('5,fpath,*', height='18px',
                                    background=DARK_TOOLBAR, color=DARK_TEXT_DIM)
        bar.fpath.div('^.module', font_size='9px')
        frame.data('.source', source)
        frame.data('.breakpoints', breakpoints)

        commandbar.savebtn.slotButton('Save', iconClass='iconbox save',
                                       _class='source_viewer_button',
                                       visible='^.changed_editor',
                                       action='PUBLISH sourceCodeUpdate={save_as:filename || false}',
                                       filename='',
                                       ask=dict(title='Save as', askOn='Shift',
                                                fields=[dict(name='filename', lbl='Name', validate_case='l')]))
        commandbar.revertbtn.slotButton('Revert', iconClass='iconbox revert', _class='source_viewer_button',
                                         action='SET .source = _oldval',
                                         visible='^.changed_editor',
                                         _oldval='=.source_oldvalue')

        frame.data('.source', source)
        frame.data('.source_oldvalue', source)
        frame.dataController("""SET .changed_editor = currval!=oldval;
                                genro.dom.setClass(bar,"changed_editor",currval!=oldval);""",
                              currval='^.source',
                              oldval='^.source_oldvalue', bar=commandbar, _onBuilt=True)
        frame.dataRpc('dummy', self.save_source_code, docPath='=.module',
                       subscribe_sourceCodeUpdate=True,
                       sourceCode='=.source', _if='sourceCode && _source_changed',
                       _source_changed='=.changed_editor', _preview_iframe=preview_iframe,
                       _onResult="""if(result.saveOk){
                                        SET .source_oldvalue = kwargs.sourceCode;
                                    }
                                    else{
                                        FIRE .error = result;
                                    }
                                """)

        cm = cmroot.codemirror(value='^.source',
                                nodeId='%s_cm' % frameCode,
                                config_mode='python', config_lineNumbers=True,
                                config_theme='monokai',
                                config_indentUnit=4, config_keyMap='softTab',
                                config_addon='search',
                                height='100%',
                                config_gutters=["CodeMirror-linenumbers", "pdb_breakpoints"],
                                onCreated="this.attributeOwnerNode('_activeIDE')._gnrIdeHandler.onCreatedEditor(this);",
                                readOnly='^.#parent.#parent.readOnly',
                                modulePath=module)
        frame.dataController("""
            var cm = cm.externalWidget;
            cm.clearGutter('pdb_breakpoints');
            if(breakpoints){
                breakpoints.forEach(function(n){
                    var line_cm = n.attr.line -1;
                    cm.setGutterMarker(line_cm, "pdb_breakpoints",cm.gnrMakeMarker(n.attr.condition));
                });
            }
            """, breakpoints='^.breakpoints', cm=cm, _fired='^.editorCompleted')
        frame.dataController("""
            var cm = cmNode.externalWidget;
            var lineno = error.lineno-1;
            var offset = error.offset-1;
            var ch_start = error.offset>1?error.offset-1:error.offset;
            var ch_end = error.offset;
            cm.scrollIntoView({line:lineno,ch:ch_start});
            var tm = cm.doc.markText({line:lineno,ch:ch_start},{line:lineno, ch:ch_end},
                            {clearOnEnter:true,className:'source_viewer_error'});
            genro.dlg.floatingMessage(cmNode.getParentNode(),{messageType:'error',
                        message:dataTemplate('Save error: $error. Line $lineno pos $offset',error),onClosedCb:function(){
                    tm.clear();
                }})
            """, error='^.error', cmNode=cm)

    def _readsource(self, docPath):
        if not os.path.exists(docPath):
            return
        with open(docPath, 'r') as f:
            return f.read()

    @public_method
    def save_source_code(self, sourceCode=None, docPath=None, save_as=None):
        sourceCode = str(sourceCode)
        if not self.source_viewer_edit_allowed():
            raise Exception('Not Allowed to write source code')
        fileExt = (os.path.splitext(docPath)[1] or '.')[1:]
        if fileExt:
            error = getattr(self, 'checkFile_%s' % fileExt, None)(sourceCode, docPath, save_as=save_as)
            if error:
                return error
        if save_as:
            save_as = save_as.strip().replace(' ', '_')
            if fileExt and not save_as.endswith('.%s' % fileExt):
                save_as = '%s.%s' % (save_as, fileExt)
            filepath = os.path.join(os.path.dirname(docPath), save_as)
        else:
            filepath = docPath
        self._writesource(sourceCode, filepath)
        return dict(saveOk=True, newpath=filepath)

    def checkFile_py(self, sourceCode, docPath, save_as=None):
        try:
            compile('%s\n' % sourceCode, 'dummy', 'exec')
            if not save_as:
                sys.modules.pop(os.path.splitext(docPath)[0].replace(os.path.sep, '_').replace('.', '_'), None)
        except SyntaxError as e:
            return dict(lineno=e.lineno, msg=e.msg, offset=e.offset)

    def checkFile_xml(self, sourceCode, docPath, save_as=None):
        try:
            Bag(sourceCode)
        except Exception as e:
            return dict(lineno=e.getLineNumber(), msg=e.getMessage(), offset=e.getColumnNumber())

    def _writesource(self, sourceCode, docPath):
        if self.source_viewer_edit_allowed():
            with open(docPath, 'w') as f:
                f.write(sourceCode)

    def source_viewer_edit_allowed(self):
        return self.site.remote_edit

    def gi_debuggerPane(self, frame):
        bc = frame.center.borderContainer()
        self.gi_debuggerTop(frame.top)
        self.gi_debuggerLeft(bc)
        self.gi_debuggerRight(bc)
        self.gi_debuggerBottom(bc)
        self.gi_debuggerCenter(bc)

    def gi_debuggerTop(self, top):
        bar = top.slotToolbar('5,stepover,stepin,stepout,cont,clearconsole,*',
                               background=DARK_TOOLBAR, color=DARK_TEXT)
        bar.stepover.slotButton('Step over', action='this.attributeOwnerNode("_activeIde")._gnrIdeHandler.do_stepOver()')
        bar.stepin.slotButton('Step in', action='this.attributeOwnerNode("_activeIde")._gnrIdeHandler.do_stepIn()')
        bar.stepout.slotButton('Step out', action='this.attributeOwnerNode("_activeIde")._gnrIdeHandler.do_stepOut()')
        bar.cont.slotButton('Continue', action='this.attributeOwnerNode("_activeIde")._gnrIdeHandler.do_continue()')
        bar.clearconsole.slotButton('Clear console', action='this.attributeOwnerNode("_activeIde")._gnrIdeHandler.clearConsole()')

    def gi_debuggerLeft(self, bc):
        bc = bc.borderContainer(width='250px', splitter=True, region='left', margin='2px',
                                 border='1px solid %s' % DARK_BORDER, margin_right=0, rounded=4)
        bc.contentPane(region='top', background=DARK_TOOLBAR, color=DARK_TEXT,
                        font_size='.8em', text_align='center', padding='2px').div('Stack')
        bc.contentPane(region='center', padding='2px', background=DARK_PANEL, color=DARK_TEXT).tree(
            storepath='.stack', labelAttribute='caption', _class='branchtree noIcon', autoCollapse=True,
            connect_onClick="""level=$1.attr.level;this.attributeOwnerNode("_activeIde")._gnrIdeHandler.do_level(level);""")

    def gi_debuggerRight(self, bc):
        bc = bc.borderContainer(width='250px', splitter=True, region='right', margin='2px',
                                 border='1px solid %s' % DARK_BORDER, margin_left=0, rounded=4)
        paneTree = bc.contentPane(region='center', background=DARK_PANEL, color=DARK_TEXT)
        tree = paneTree.treeGrid(storepath='.result', headers=True)
        tree.column('__label__', contentCb="""return this.attr.caption || this.label""", header='Variable')
        tree.column('__value__', size=300, contentCb="""var v=this.getValue();
                                                          return (v instanceof gnr.GnrBag)?'':_F(v)""",
                    header='Value')

    def gi_debuggerCenter(self, bc):
        bc = bc.borderContainer(region='center', border='1px solid %s' % DARK_BORDER,
                                 margin='2px', margin_right=0, margin_left=0, rounded=4)
        bc.contentPane(region='top', background=DARK_TOOLBAR, color=DARK_TEXT,
                        font_size='.8em', text_align='center', padding='2px').div('Output')
        center = bc.contentPane(region='center', padding='2px', border_bottom='1px solid %s' % DARK_BORDER,
                                 _class='selectable', overflow='auto', background=DARK_BG, color=DARK_TEXT)
        center.div(value='^.output', style='font-family:monospace; white-space:pre-wrap')
        lastline = center.div(position='relative')
        lastline.div('>>>', position='absolute', top='1px', left='0px', color='#569cd6')
        debugger_input = lastline.div(position='absolute', top='0px', left='20px', right='5px').input(
            value='^.command', width='100%', border='0px',
            background=DARK_BG, color=DARK_TEXT)
        center.dataController("""SET .output=output? output+_lf+line:line;""",
                               line='^.output_line', output='=.output')
        center.dataController("""SET .output_line=command;
                                 if (command[0]=='/'){
                                    command=command.slice(1)
                                 }else if(command[0]!='!'){
                                     command='!'+command;
                                 }
                                 this.attributeOwnerNode('_activeIDE').publish('debugCommand',{command:command});
                                 SET .command=null;
                                 debugger_input.domNode.focus();
                                 """, command='^.command', debugger_input=debugger_input, _if='command')

    def gi_debuggerBottom(self, bottom):
        pass

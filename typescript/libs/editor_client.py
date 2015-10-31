﻿from .reference import RefInfo
from .node_client import ServerClient, WorkerClient
from .service_proxy import ServiceProxy
from .global_vars import *

from .logger import *
from .telemetry import *

class ClientFileInfo:
    """per-file, globally-accessible information"""

    def __init__(self, filename):
        self.filename = filename
        self.pending_changes = False
        self.change_count = 0
        self.errors = {
            'syntacticDiag': [],
            'semanticDiag': [],
        }
        self.rename_on_load = None


class EditorClient:
    """A singleton class holding information for the entire application that must be accessible globally"""

    def __init__(self):
        self.file_map = {}
        self.ref_info = None
        self.seq_to_tempfile_name = {}
        self.available_tempfile_list = []
        self.tmpseq = 0
        self.node_client = None
        self.worker_client = None
        self.service = None
        self.initialized = False

        self.tab_size = 4
        self.indent_size = 4
        self.translate_tab_to_spaces = False

        self.ts_auto_format_enabled = True
        self.ts_auto_indent_enabled = True
        self.auto_match_enabled = True
        
        self.send_metrics = False
        self.telemetry_user_id = None
        # default is true but only actually on by default once telemetry accepted
        self.check_for_dts_updates = True

    def initialize(self):
        """
        Sublime_api methods can only be executed in plugin_loaded, and they will
        return None if executed during import time. Therefore the cli needs to be
        initialized during loading time
        """

        # retrieve the path to tsserver.js
        # first see if user set the path to the file
        settings = sublime.load_settings('Preferences.sublime-settings')
        proc_file = settings.get('typescript_proc_file')
        if not proc_file:
            # otherwise, get tsserver.js from package directory
            proc_file = os.path.join(PLUGIN_DIR, "tsserver", "tsserver.js")
        print("spawning node module: " + proc_file)

        self.node_client = ServerClient(proc_file)
        self.worker_client = WorkerClient(proc_file)
        self.service = ServiceProxy(self.worker_client, self.node_client)

        # load formatting and telemetry settings and set callbacks for setting changes
        for editor_setting_name in [
            'tab_size',
            'indent_size',
            'translate_tabs_to_spaces',
            'typescript_auto_format',
            'typescript_auto_indent',
            'auto_match_enabled',
            TELEMETRY_SETTING_NAME,
            CHECK_FOR_DTS_SETTING
        ]:
            settings.add_on_change(editor_setting_name, self.load_editor_settings)
        self.load_editor_settings()

        self.initialized = True

    def load_editor_settings(self):
        settings = sublime.load_settings('Preferences.sublime-settings')
        self.tab_size = settings.get('tab_size', 4)
        self.indent_size = settings.get('indent_size', 4)
        self.translate_tab_to_spaces = settings.get('translate_tabs_to_spaces', False)
        self.ts_auto_format_enabled = settings.get("typescript_auto_format")
        self.ts_auto_indent_enabled = settings.get("typescript_auto_indent")
        self.auto_match_enabled = settings.get("auto_match_enabled")

        telemetry_acceptance = settings.get(TELEMETRY_SETTING_NAME, False)
        self.send_metrics = False if not telemetry_acceptance else telemetry_acceptance['accepted']
        self.telemetry_user_id = None if not telemetry_acceptance else telemetry_acceptance['userID']
        check_dts_setting = settings.get(CHECK_FOR_DTS_SETTING, True)
        self.check_for_dts_updates = False if not telemetry_acceptance else check_dts_setting

        self.set_features()

    def set_features(self):
        host_info = "Sublime Text version " + str(sublime.version())
        # Preferences Settings
        editor_options = {
            "tabSize": self.tab_size,
            "indentSize": self.indent_size,
            "convertTabsToSpaces": self.translate_tab_to_spaces,
            "sendMetrics": self.send_metrics,
            "telemetryUserID": self.telemetry_user_id,
            "checkForDtsUpdates": self.check_for_dts_updates
        }

        self.service.configure(host_info, None, editor_options)

    # ref info is for Find References view
    # TODO: generalize this so that there can be multiple
    # for example, one for Find References and one for build errors
    def dispose_ref_info(self):
        self.ref_info = None

    def init_ref_info(self, first_line, ref_id):
        self.ref_info = RefInfo(first_line, ref_id)
        return self.ref_info

    def update_ref_info(self, ref_info):
        self.ref_info = ref_info

    def get_ref_info(self):
        return self.ref_info

    def get_or_add_file(self, filename):
        """Get or add per-file information that must be globally accessible """
        if os.name == "nt" and filename:
            filename = filename.replace('/', '\\')
        if filename not in self.file_map:
            client_info = ClientFileInfo(filename)
            self.file_map[filename] = client_info
        else:
            client_info = self.file_map[filename]
        return client_info

    def has_errors(self, filename):
        client_info = self.get_or_add_file(filename)
        return len(client_info.errors['syntacticDiag']) > 0 or len(client_info.errors['semanticDiag']) > 0

# The globally accessible instance
cli = EditorClient()
# import sublime, sublimeplugin
import subprocess
import json
import os

import sublime, sublime_plugin

pluginName = "GoShowDefinition"

def error(*msg):
    print("%s [ERROR]:" % pluginName, msg[0:])

def debug(*msg):
    if settings("debug", False):
        print("%s [DEBUG]:" % pluginName, msg[0:])

def settings(key, default):
    return sublime.active_window().active_view().\
        settings().get('go_show_definition', {}).get(key, default)

def plugin_loaded():
    debug(os.environ.get("PATH"))

class GoShowDefinitionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_name = self.file_name()
        if file_name == "":
            return

        offset = self.offset()
        if offset == 0:
            return

        self.runGuru('describe', file_name, offset)

    def file_name(self):
        return self.view.file_name()

    def offset(self):
        region = self.view.sel()[0]
        text = self.view.substr(sublime.Region(0, region.end()))

        return len(text.encode('utf-8'))

    def content(self):
        return self.view.substr(sublime.Region(0, self.view.size()))

    def runGuru(self, mode, file_path, offset):
        cmd = "%(guru_bin)s -modified -json %(mode)s %(file_path)s:#%(offset)s" % {
            "guru_bin": settings('bin', 'guru'),
            "mode": mode,
            "file_path": file_path,
            "offset": offset,
        }
        debug("cmd", cmd)
        cmd_env = {}
        sublime.set_timeout_async(
            lambda: self.runInThread(cmd, cmd_env, file_path, self.content(), self.handleCommandResult),
            0
        )

    def runInThread(self, cmd, env, file_path, content, callback):
        contentbytes = content.encode('utf-8',errors = 'strict')
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True, env=env)
        proc.stdin.write(bytes(file_path+'\n', encoding='utf8'))
        proc.stdin.write(bytes(str(len(contentbytes))+'\n', encoding='utf8'))
        proc.stdin.write(contentbytes)
        out, err = proc.communicate()
        callback(out.decode('utf-8'), err.decode('utf-8'))

    def handleCommandResult(self, stdout, stder):
        if stder != "":
            error(stder)
            return

        if stdout == "":
            debug("Empty guru output")
            return

        try:
            data = json.loads(stdout)
        except ValueError:
            error("cannot parse guru output")

        debug(data)
        self.showPopup(self.formatData(data))

    def formatData(self, data):
        key = data.get("detail")

        debug(key)
        if key == None:
            return

        elif key == "type":
            return self.formatType(data[key])

        elif key == "value":
            return self.formatValue(data[key])

        else:
            return "unknown type `%s`" % key

    def formatType(self, data):
        return """
            type: %(type)s
            <br />
            namedef: %(def)s
        """ % {
            "type": data.get("type"),
            "def": data.get("namedef"),
        }

    def formatValue(self, data):
        return """
            type: %(type)s
        """ % {
            "type": data.get("type"),
        }

    def showPopup(self, text):
        html = """
            <body id=show-definition>
                <style>
                    p {
                        margin-top: 0;
                    }
                    a {
                        font-family: system;
                        font-size: 1.05rem;
                    }
                </style>
                <p>%(text)s</p>
            </body>
        """ % {"text": text}

        # self.view.show_popup(html, max_width=512, on_navigate=lambda x: pass)
        self.view.show_popup(html, max_width=512)

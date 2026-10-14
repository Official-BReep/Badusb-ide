import sys
sys.path.insert(0, '.')
import scriptmonkey_app
from lib.Ducky_Highlighter import DuckyHighlighter as D
from lib.js_highlighter import JavaScriptHighlighter as J
print('IMPORT_OK', scriptmonkey_app.DuckyHighlighter is D, scriptmonkey_app.JavaScriptHighlighter is J)

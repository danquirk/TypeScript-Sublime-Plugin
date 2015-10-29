import sys
import os
import uuid
import subprocess
from time import gmtime, strftime
import json

if sys.version_info < (3, 0):
    from .global_vars import *
    import urllib2
else:
    from .global_vars import *
    from urllib.request import *
    import urllib.request

def init_telemetry(settings):
    this_file = os.path.abspath(__file__)
    privacy_file = this_file[0:this_file.rfind(os.path.sep)] + os.path.sep + "../../privacyPolicy.txt"
    sublime.active_window().open_file(privacy_file)
    diagText = "The TypeScript plugin collects your usage data and sends it to Microsoft to help improve the product. We never use this information to identify you or contact you.\n\nIf you do not want your usage data to be sent to Microsoft click Decline, otherwise click Accept. You can also change these settings later. \n\nPlease go to www.typescriptlang.org/sublimetelemetry for more information."
    res = sublime.yes_no_cancel_dialog(diagText, "Accept", "Decline")
    acceptance_result = True if res == sublime.DIALOG_YES else False
    
    # If the user has an existing telemetry ID, re-use it
    # If they have none and accept telemetry generate a random GUID for an ID
    existing_telemetry_setting = settings.get(TELEMETRY_SETTING_NAME, None) 
    current_telemetry_user_id =  "None" if not existing_telemetry_setting else existing_telemetry_setting["userID"]
    if acceptance_result == True and current_telemetry_user_id == "None":
        current_telemetry_user_id = str(uuid.uuid4())

    telemetry_settings_value = { "version": PRIVACY_POLICY_VERSION, "accepted": acceptance_result, "userID": current_telemetry_user_id } 

    settings.set(TELEMETRY_SETTING_NAME, telemetry_settings_value) 
    sublime.save_settings("Preferences.sublime-settings")
    _send_telemetry_acceptance_result(acceptance_result)

def _send_telemetry_acceptance_result(acceptance_result):
    appInsightsURL = "https://dc.services.visualstudio.com/v2/track"
    values = {
                'iKey': '78e2d1f3-b56d-47d8-9b9a-fa4c056a0f21',
                'name': 'Microsoft.ApplicationInsights.Event',
                'time': strftime("%Y-%m-%d %H:%M:%S", gmtime()),
                'data': {
                    'baseType': 'EventData',
                    'baseData': {
                        'ver': 2,
                        'name': 'TypeScriptTelemetryAcceptanceEvent',
                        'measurements': {},
                        'properties': { 'optedIn': acceptance_result }
                    }
                }
            }

    headers = {'Content-Type': 'application/json; charset=utf-8'}
    jsondata = json.dumps(values)
    binary_data = jsondata.encode('utf-8')
    if sys.version_info < (3, 0):
        # TODO: test this
        lib = urllib2
        urlopen = lib.urlopen

        request = urllib2.Request(appInsightsURL, data = values, headers = headers)
        response = urllib2.urlopen(request)
    else:
        lib = urllib
        urlopen = lib.request.urlopen
        headers["Content-Length"] = len(binary_data)
    
        request = urllib.request.Request(appInsightsURL, data = binary_data, headers = headers)
        response = urllib.request.urlopen(request)
    #request = lib.Request(appInsightsURL, data = binary_data, headers = headers)

    #try:
    #    response = urlopen(request)
    #except lib.error.HTTPError as e:
    #    logger.log.error(e.code);
    #    logger.log.error(e.read());

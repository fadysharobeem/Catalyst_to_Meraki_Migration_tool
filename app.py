from ciscoconfparse import CiscoConfParse
from flask import Flask, render_template, request, redirect, url_for, session
import os, requests, json, pprint, re, usr_info
from collections import defaultdict
from flask_session import Session

Bot_Bearer = usr_info.Bot_Bearer
base_url = "https://api.meraki.com/api/v0/"
webex_url = "https://api.ciscospark.com/v1/messages"

payload = {}
organizations = {}
api = ""
payload = None

app = Flask(__name__)
app.config['SECRET_KEY']  = os.urandom(128)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

sw_list = []
configured_ports = defaultdict(list)
unconfigured_ports = defaultdict(list)

def Meraki_config(api,sw_list,my_dict,Downlink_list):
    #Webex teams Payload
    def Webex_payload(success,failed):
        payload =""
        payload ='''
\u2713 Ports that configured successfully
%s
\u2717 Ports that failed to be configured
%s
----------------------------------------------------------
'''%(str(success),str(failed))
        return payload

    def Webex_Teams(message,To_email):
        body = {"toPersonEmail": To_email, "text":message}
        headers = {"Content-type":"application/json", "Authorization": "Bearer " + Bot_Bearer}
        response = requests.post(url=webex_url, json=body, headers=headers)
        print(response.text)

    def config_access_port(serial,p_number,desc,active,mode,data_Vlan,voice_Vlan,mac,mac_limit):
        headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Cisco-Meraki-API-Key": api
                    }
        url = "https://api.meraki.com/api/v0/devices/"+serial+"/switchPorts/"+str(p_number)

        payload = '''{
            "name": "%s",
            "tags": "",
            "enabled": %s,
            "poeEnabled": true,
            "type": "%s",
            "vlan": %s,
            "voiceVlan": %s,
            "isolationEnabled": false,
            "rstpEnabled": true,
            "stpGuard": "disabled",
            "linkNegotiation": "Auto negotiate",
            "stickyMacWhitelist": %s,
            "stickyMacWhitelistLimit": %s
            }'''% (desc,active,mode,data_Vlan,voice_Vlan,mac,mac_limit)
        print(payload)
        response = requests.request('PUT', url, headers=headers, data = payload)
        if response.status_code == 200:
            configured_ports[serial].append(p_number)
            print(json.loads(response.text))
        else:
            print(response.status_code)
            unconfigured_ports[serial].append(p_number)

    def config_access_port_no_Mac(serial,p_number,desc,active,mode,data_Vlan,voice_Vlan):
        headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Cisco-Meraki-API-Key": api
                    }
        url = "https://api.meraki.com/api/v0/devices/"+serial+"/switchPorts/"+str(p_number)

        payload = '''{
            "name": "%s",
            "tags": "",
            "enabled": %s,
            "poeEnabled": true,
            "type": "%s",
            "vlan": %s,
            "voiceVlan": %s,
            "isolationEnabled": false,
            "rstpEnabled": true,
            "stpGuard": "disabled",
            "linkNegotiation": "Auto negotiate",
            "accessPolicyNumber": null
            }'''% (desc,active,mode,data_Vlan,voice_Vlan)
        print(payload)
        response = requests.request('PUT', url, headers=headers, data = payload)

        if response.status_code == 200:
            configured_ports[serial].append(p_number)
            print(json.loads(response.text))
        else:
            print(response.status_code)
            unconfigured_ports[serial].append(p_number)

    def config_access_port_trunk(serial,p_number,desc,active,mode,native_vlan,allowed_vlan):
        headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Cisco-Meraki-API-Key": api
                    }
        url = "https://api.meraki.com/api/v0/devices/"+serial+"/switchPorts/"+str(p_number)

        payload = '''{
            "name": "%s",
            "tags": "",
            "enabled": %s,
            "poeEnabled": true,
            "type": "%s",
            "vlan": %s,
            "allowedVlans": "%s",
            "isolationEnabled": false,
            "rstpEnabled": true,
            "stpGuard": "disabled",
            "linkNegotiation": "Auto negotiate",
            "accessPolicyNumber": null
            }'''% (desc,active,mode,native_vlan,allowed_vlan)
        print(payload)
        response = requests.request('PUT', url, headers=headers, data = payload)

        if response.status_code == 200:
            configured_ports[serial].append(p_number)
            print(json.loads(response.text))
        else:
            print(response.status_code)
            unconfigured_ports[serial].append(p_number)

    def config_shut(serial,p_number):
        headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Cisco-Meraki-API-Key": api
                    }
        url = "https://api.meraki.com/api/v0/devices/"+serial+"/switchPorts/"+str(p_number)

        payload = '''{
            "enabled": false
            }'''
        print(payload)
        response = requests.request('PUT', url, headers=headers, data = payload)

        if response.status_code == 200:
            configured_ports[serial].append(p_number)
            print(json.loads(response.text))
        else:
            print(response.status_code)
            unconfigured_ports[serial].append(p_number)

    ## Loop to go through all the ports of the switches
    def loop_configure_meraki(my_dict,Downlink_list):
        try:
            y = 0
            #Loop to get all the interfaces in the my_dict
            while y <= len(Downlink_list)-1:
                x = Downlink_list[y]
                print("\n----------- "+x+" -----------")
                pprint.pprint(my_dict[Downlink_list[y]])
                ## Check if the interface mode is configured as Access
                if my_dict[x]['mode'] == "access":
                    try:
                        if not my_dict[x]['voice_Vlan'] == "":
                            Voice_vlan = my_dict[x]['voice_Vlan']
                    except:
                        my_dict[x]['voice_Vlan'] = "null"
                    try:
                        if not my_dict[x]['desc'] == "":
                            description = my_dict[x]["desc"]
                    except:
                        my_dict[x]["desc"] = ""
                    try:
                        if not my_dict[x]['mac'] == []:
                            pass
                    except:
                        pass
                    try:
                        if not my_dict[x]['data_Vlan'] == "":
                            data_vlan = my_dict[x]['data_Vlan']
                    except:
                        my_dict[x]['data_Vlan'] = "1"
                        data_vlan = my_dict[x]['data_Vlan']
                    try:
                        if not my_dict[x]['Port_Sec'] == "":
                            mac_limit = my_dict[x]['Port_Sec']
                    except:
                        my_dict[x]['Port_Sec'] = ""

                ## Check the switch that mapped to those catalyst ports
                    sw = int(my_dict[x]['sw_module'])-1
                    print("Switch Serial Number "+sw_list[sw])

                ## Test if the interface has Port security configured or not then apply the right Meraki configuration
                    if my_dict[x]['Port_Sec'] == "":
                        config_access_port_no_Mac(sw_list[sw],my_dict[x]['port'],my_dict[x]["desc"],my_dict[x]["active"],my_dict[x]['mode'],my_dict[x]['data_Vlan'],my_dict[x]['voice_Vlan'])
                    else:
                        config_access_port(sw_list[sw],my_dict[x]['port'],my_dict[x]["desc"],my_dict[x]["active"],my_dict[x]['mode'],my_dict[x]['data_Vlan'],my_dict[x]['voice_Vlan'],json.dumps(my_dict[x]['mac']),my_dict[x]['Port_Sec'])
                ## Check if the interface mode is configured as Trunk
                if my_dict[x]['mode'] == "trunk":
                    try:
                        if not my_dict[x]['desc'] == "":
                            description = my_dict[x]["desc"]
                    except:
                        my_dict[x]["desc"] = ""
                    try:
                        if not my_dict[x]['native'] == "":
                            native_vlan = my_dict[x]['native']
                    except:
                        my_dict[x]['native'] = "1"
                        native_vlan = my_dict[x]['native']
                    try:
                        if not my_dict[x]['trunk_allowed'] == "":
                            trunk_allow = my_dict[x]['trunk_allowed']
                    except:
                        my_dict[x]['trunk_allowed'] = "1-1000"

                    sw = int(my_dict[x]['sw_module'])-1
                    try:
                        config_access_port_trunk(sw_list[sw],my_dict[x]['port'],my_dict[x]["desc"],my_dict[x]["active"],my_dict[x]['mode'],my_dict[x]['native'],my_dict[x]['trunk_allowed'])
                    except:
                        print("Error in configuring Trunk port "+my_dict[x])
                ## If the interface is not configured as access or trunk just pass
                if my_dict[x]['mode'] == "":
                    if my_dict[x]["active"] == "false":
                        config_shut(sw_list[sw],my_dict[x]['port'])
                    else:
                        pass
                y +=1

        except:
            print("Can't find port " + str(y))
            pass

    loop_configure_meraki(my_dict,Downlink_list)
    try:
        Webex_Teams(Webex_payload(configured_ports,unconfigured_ports),session["webex_email"])
    except:
        print(f"Couldn't send message to Webex Teams")

def Start(API, sw_list,Cisco_SW_config,webex_email):
    my_dict = {}
    ## List of interfaces that are shut
    shut_interfaces = []

    def split_down_up_link(interfaces_list, Gig_uplink):
        Uplink_list=[]
        Downlink_list=[]
        Other_list =[]

        #Creating a copy of the interface list to avoid Runtime error
        interfaces_list_copy = interfaces_list.copy()

        for key, value in interfaces_list.items():
        #TengigbitEthernet ports stright away considered as uplinks
            if key == "TenGigabitEthernet":
                for value in interfaces_list_copy["TenGigabitEthernet"]:
                    Uplink_list.append(value)
        #GigbitEthernet ports to be evaluated if has 1 in subnetwork module (x/1/x) then its uplink otherwise will be downlink
            if key == "GigabitEthernet":
               for value in interfaces_list_copy["GigabitEthernet"]:
                   if value in Gig_uplink:
                       Uplink_list.append(value)
                   if len(interfaces_list_copy["FastEthernet"]) > 4 and len(interfaces_list_copy["GigabitEthernet"]) < 5:
                       Uplink_list.append(value)
                   elif value not in Gig_uplink:
                       Downlink_list.append(value)
        #FastEthernet to be checked if has more than 4 ports in the list then they all downlink
            if key == "FastEthernet"  and len(interfaces_list_copy["FastEthernet"]) > 4:
                for value in interfaces_list["FastEthernet"]:
                    Downlink_list.append(value)
        #Single FastEthernet interface to be considered as others
            if key =="FastEthernet"  and len(interfaces_list_copy["FastEthernet"]) <=1:
                for value in interfaces_list_copy["FastEthernet"]:
                    Other_list.append(value)

            else:
                for value in interfaces_list_copy[key]:
                    if key=="TenGigabitEthernet" or key=="GigabitEthernet" or key=="FastEthernet":
                        pass
                    else:
                        Other_list.append(value)
        return Uplink_list, Downlink_list, Other_list

    ## rebuild the mac address to match Meraki format
    def mac_build(my_str, group=2, char=':'):
        port_sec = re.findall(re.compile(r'[a-fA-F0-9.]{14}'), my_str)[0]
        p = re.compile(r'^[a-fA-F0-9.]{14}')
        new_p = re.sub("\.","",port_sec)
        my_str = str(new_p)

        last = char.join(my_str[i:i+group] for i in range(0, len(my_str), group))
        return last

    ## Extract out the details of the switch module and the port number
    def check(intf):
        parse = CiscoConfParse(Cisco_SW_config, syntax='ios', factory=True)

        intf_rgx = re.compile(r'interface GigabitEthernet(\d+)\/(\d+)\/(\d+)$')

        for obj in parse.find_objects(intf):
            Sub_module = None
            port = obj.ordinal_list[-1]
            if intf_rgx.search(obj.text) is not None:
                Sub_module = obj.ordinal_list[-2]

            return port,Sub_module

    def read_Cisco_SW():
        ##Parsing the Cisco Catalyst configuration (focused on the interface config)
        print("-------- Reading <"+Cisco_SW_config+"> Configuration --------")
        parse = CiscoConfParse(Cisco_SW_config, syntax='ios', factory=True)

        x = 0
        Gig_uplink=[]
        All_interfaces= defaultdict(list)
        ## Select the interfaces
        intf = parse.find_objects('^interface')
        for intf_obj in parse.find_objects_w_child('^interface', '^\s+shutdown'):
            shut_interfaces.append(intf_obj.re_match_typed('^interface\s+(\S.+?)$'))
        #print(f"These are the shut interfaces: {shut_interfaces}")

        for intf_obj in intf:
            ## Get the interface name
            intf_name = intf_obj.re_match_typed('^interface\s+(\S.*)$')
            #Only interface name will be used to catogrize different types of interfaces (downlink and uplink)
            only_intf_name = re.sub("\d+|\\/","",intf_name)
            Switch_module = intf_obj.re_match_typed('^interface\s\S+?thernet+(\d)')
            test_port_numerb = intf_obj.re_match_typed('^interface\s\S+?thernet+(\S+?)')

            All_interfaces[only_intf_name].append(intf_name)

            my_dict[intf_name] = {}
            my_dict[intf_name]['sw_module'] = "1"
            my_dict[intf_name]['desc'] = ""
            my_dict[intf_name]['port'] = ""
            my_dict[intf_name]['mode'] = ""
            my_dict[intf_name]['mac'] = []
            my_dict[intf_name]['active'] = "true"

            try:
                port,sub_module = check(intf_name)
                if sub_module == 1:
                    Gig_uplink.append(intf_name)

                if Switch_module == 0:
                    my_dict[intf_name]['sw_module'] = 1
                if not Switch_module == "" and not Switch_module == 0:
                    my_dict[intf_name]['sw_module'] = Switch_module

                else:
                    pass

                my_dict[intf_name]['port'] = port
                my_dict[intf_name]['mac'].clear()
                ## check if the interface in the shutdown list then mark it as shutdown
                if intf_name in shut_interfaces:
                    my_dict[intf_name]['active'] = "false"

                int_fx = intf[x].children
                ## Add 1 to capture the next interface
                x += 1
                ## Capture the configuration of the interface
                for child in int_fx:
                    desc = child.re_match_typed(regex=r'\sdescription\s+(\S.+)')
                    Vlanv = child.re_match_typed(regex=r'\sswitchport\svoice\svlan\s+(\S.*)')
                    port_mode = child.re_match_typed(regex=r'\sswitchport\smode\s+(\S.+)')
                    Vlan = child.re_match_typed(regex=r'\sswitchport\saccess\svlan\s+(\S.*)')
                    port_sec_raw = child.re_match_typed(regex=r'\sswitchport\sport-security\smac-address\ssticky\s+(\S.+)')
                    trunk_native = child.re_match_typed(regex=r'\sswitchport\strunk\snative\svlan\s+(\S.*)')
                    trunk_v_allowed = child.re_match_typed(regex=r'\sswitchport\strunk\sallowed\svlan\s+(\S.*)')
                    speed = child.re_match_typed(regex=r'\sspeed\s+(\S.*)')
                    duplex = child.re_match_typed(regex=r'\sduplex\s+(\S.+)')
                    port_channel = child.re_match_typed(regex=r'\schannel-group\s+(\d)')
                    max_mac = child.re_match_typed(regex=r'\sswitchport\sport-security\smaximum\s+(\d)')

                    if not desc == "":
                        my_dict[intf_name]['desc'] = desc
                    if not port_mode == "":
                        my_dict[intf_name]['mode'] = port_mode
                    if not Vlan == "":
                        my_dict[intf_name]['data_Vlan'] = Vlan
                    if not Vlanv == "":
                        my_dict[intf_name]['voice_Vlan'] = Vlanv
                    if not port_sec_raw == "":
                        my_dict[intf_name]['mac'].append(mac_build(port_sec_raw))
                    if not trunk_native == "":
                        my_dict[intf_name]['native'] = trunk_native
                    if not trunk_v_allowed == "":
                        my_dict[intf_name]['trunk_allowed'] = trunk_v_allowed
                    if not speed == "":
                        my_dict[intf_name]['speed'] = speed
                    if not duplex == "":
                        my_dict[intf_name]['duplex'] = duplex
                    if not port_channel == "":
                        my_dict[intf_name]['LACP_Group'] = port_channel
                    if not max_mac == "":
                        my_dict[intf_name]['Port_Sec'] = max_mac
                    else:
                        pass

            except:
                print(f"Error in ready interface {intf_name}")

        Uplink_list, Downlink_list, Other_list = split_down_up_link(All_interfaces,Gig_uplink)
        return Uplink_list, Downlink_list, Other_list, my_dict

    Uplink_list, Downlink_list, Other_list, my_dict = read_Cisco_SW()
    return Uplink_list, Downlink_list, Other_list,my_dict

@app.route('/')
def index():
    session.clear()
    return render_template("input.html")

@app.route('/confirm', methods=["POST"])
def confirm():
    data = session["ToBeConfigured"]
    Downlink_list = session["Downlink_list"]
    api = session["api"]
    sw_list = session["sw_list"]
    #Start the meraki config migration after confirmation from the user
    Meraki_config(api,sw_list,data,Downlink_list)
####Check the return from thr Meraki_config function and make it part of the session
    return render_template("Success.html", configured_ports=configured_ports, unconfigured_ports=unconfigured_ports)

@app.route('/api', methods=["POST"])
def api():
    sw_list.clear()
    configured_ports.clear()
    unconfigured_ports.clear()
    api=None
    #Get the info of the form
    session["api"] = request.form["fname"]
    session["webex_email"] = request.form["Webex_email"]
    uploaded_file = request.files['file']
    dir = os.path.join(os.getcwd(),"static/files")
    if uploaded_file.filename != '':
        uploaded_file.save(os.path.join(dir,uploaded_file.filename))

    sw_stack = int(request.form["member"])
    #List of the fields in the form for the switch stack
    i = 0
    while i < int(sw_stack):
        sw_list.append(request.form["member" +str(i)])
        i +=1

    session["sw_list"] = sw_list
    session["sw_file"] = os.path.join(dir,uploaded_file.filename)

    api = session["api"]
    webex_email = session["webex_email"]
    sw_file = session["sw_file"]

    session["Uplink_list"], session["Downlink_list"], session["Other_list"], session["my_dict"] = Start(api,session["sw_list"],sw_file,webex_email)

    #Creating a list to select the configuration parts to push to Meraki
    ToBeConfigured = {}
    z = 0
    Downlink_list = session["Downlink_list"]
    my_dict = session["my_dict"]
    while z < len(Downlink_list):
        interface = Downlink_list[z]
        ToBeConfigured[interface] = my_dict[interface]
        z +=1

    session["ToBeConfigured"] = ToBeConfigured

    return render_template("confirm.html", ToBeConfigured=session["ToBeConfigured"], Downlink_list=session["Downlink_list"])

@app.route('/drop')
def drop():
    #session.pop('api', None)
    session.clear()
    return render_template("input.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

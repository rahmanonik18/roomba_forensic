import pprint
import requests,urllib.parse,getpass,logging,argparse
from AwsRequest import AwsRequest
from flask import Flask, request, jsonify, render_template, session,send_file, render_template_string
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
import io
import json
import matplotlib.patches as patches
import numpy as np 
import getpass
import datetime
from io import BytesIO
import matplotlib.lines as mlines
import uuid
import datetime
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches

class IrobotAuthorization:
    app_id = None
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def login(self):
        response = requests.get("https://disc-prod.iot.irobotapi.com/v1/discover/endpoints?country_code=US")
        res_json = response.json()
        deployment = res_json['deployments'][next(iter(res_json['deployments']))]
        self.httpBase = deployment['httpBase']
        iotBase = deployment['httpBaseAuth']
        iotUrl = urllib.parse.urlparse(iotBase)
        self.iotHost = iotUrl.netloc
        region = deployment['awsRegion']
        self.apikey = res_json['gigya']['api_key']
        #print('self.apikey',self.apikey)
        self.gigyaBase = res_json['gigya']['datacenter_domain']
        data = {"apiKey": self.apikey,
                "targetenv": "mobile",
                "loginID": self.username,
                "password": self.password,
                "format": "json",
                "targetEnv": "mobile",
                }
        response = requests.post(
            "https://accounts.%s/accounts.login" % self.gigyaBase, data=data)
        res_json = response.json()
        #print(f"account_login_json: {res_json}")
        uid = res_json['UID']
        uidSig = res_json['UIDSignature']
        sigTime = res_json['signatureTimestamp']
        profile = res_json['profile']
        global app_id
        # data = {
        #     "id": uuid.uuid4()
        # }
        # # Convert the UUID to a string
        # data["id"] = str(data["id"])

        # # Serialize to JSON
        # app_id = json.dumps(data)
        # print(app_id)

        app_id ="ANDROID-C9A59D96-1E8C-487D-957A-64478C2EE082"# "ANDROID-" + str(uuid.uuid4()).upper()
        #app_id ="ANDROID-" + str(uuid.uuid4()).upper()
        #print(app_id)
        data = {
            "app_id": app_id,
            "assume_robot_ownership": "0",
            "gigya": {
                "signature": uidSig,
                "timestamp": sigTime,
                "uid": uid,
            }
        }
        response = requests.post("%s/v2/login" % self.httpBase, json=data)
        res_json = response.json()
        #print(f"v2_login_json: {res_json}")
        access_key = res_json['credentials']['AccessKeyId']
        secret_key = res_json['credentials']['SecretKey']
        session_token = res_json['credentials']['SessionToken']
        self.data = res_json
        self.amz = AwsRequest(region, access_key, secret_key,
                              session_token, "execute-api")
        
        
    def get_details(self):
        return self.data['robots']
    
    def get_credentials(self):
        robot_keys = self.data['robots'].keys()
        device_id = next(iter(robot_keys))
        return device_id
    def info(self):
        return self.data
    def get_maps(self, robot):
        r = (self.amz.get(self.iotHost, '/v1/%s/pmaps' % robot, query="activeDetails=2")).json()
        pmaps = []
        for map_dict in r:
            pmap_id = map_dict['pmap_id']
            pmapv_id = map_dict['active_pmapv_details']['active_pmapv']['pmapv_id']
            pmaps.append([pmap_id, pmapv_id])
        return pmaps

    def view_maps(self,robot,pmap,pmapv):
        r = (self.amz.get(self.iotHost, '/v1/%s/pmaps/%s/versions/%s/umf' % (robot,pmap,pmapv), query="activeDetails=2")).json()
        #print("view_map",r)
        return r
     
    def view_mission_history(self, robot):
       r = (self.amz.get(self.iotHost, '/v1/%s/missionhistory' % robot, query="app_id=%s" % app_id)).json()
       #r = (self.amz.get(self.iotHost, '/v1/%s/missionhistory' % robot, query="supportedDoneCodes=dndEnd,returnHomeEnd")).json()
       with open('r.json', 'w') as f:
          json.dump(r, f)
       #timeestimates----url
       #r = (self.amz.get(self.iotHost, '/v1/robots/%s/time-estimates' % (robot), query="app_id=%s" % app_id)).json()
       return r
    
    def time_estimation(self,robot):
        r = (self.amz.get(self.iotHost, '/v1/robots/%s/time-estimates' % (robot), query="app_id=%s" % app_id)).json()
        return r
    

    def account_info(self,robot):
        r = (self.amz.get(self.iotHost, '/v1/robots/%s/time-estimates' % (robot), query="app_id=%s" % app_id)).json()
        return r
      


def plot_map(points2d, borders, poses2d,typed_poses,objects,doors,hazards_data):
    # Create figure and axes
     #fig, ax = plt.subplots()
     fig, ax = plt.subplots(figsize=(15, 8))
     doc_dot = None
        # Prepare to plot borders
     for border in borders:
            border_coordinates = [points2d[id] for id in border['geometry']['ids'][0]]
            border_polygon = patches.Polygon(border_coordinates, fill=True, alpha=0.3)
            ax.add_patch(border_polygon)
        # Prepare to plot poses
    

     start_pose_ids = typed_poses['start_pose']['geometry']['ids']
     end_pose_ids = typed_poses['end_pose']['geometry']['ids']
     dock_pose_ids = typed_poses['dock_poses']['geometry']['ids']

     for pose in poses2d:
            x, y = pose['coordinates']
            ori_rad = pose['ori_rad']
            pose_id = pose['id']

             # Check if pose_id is in dock_pose_ids
            if pose_id in dock_pose_ids:
                doc_dot = ax.plot(x, y, 'bo', label='Docker position')[0]
                x, y = pose['coordinates']
                # roomba_radius = 0.05  # Adjust this value as needed
                # roomba_circle = patches.Circle((x, y), roomba_radius, fc='blue', label='Docker position')
                # ax.add_patch(roomba_circle)
                dx, dy = np.cos(ori_rad), np.sin(ori_rad)
                ax.arrow(x, y, dx, dy, head_width=0.05, head_length=0.1, fc='black', ec='black')
            # Check if pose_id is in start_pose_ids
            elif pose_id in start_pose_ids:
                start_dot = ax.plot(x, y, 'go', label='Start point')[0]
            # Otherwise, it's an end pose
            else:
                end_dot = ax.plot(x, y, 'ro', label='End point')[0]
                    
            
                

     # Plot doors
     for door_coords in doors:
        x_values, y_values = zip(*door_coords)
        ax.plot(x_values, y_values, 'm-', linewidth=2, label='Door')

     door_legend = mlines.Line2D([], [], color='magenta', lw=2, label='Door')


    
     arrow_legend = mlines.Line2D([], [], color='black', marker='>', linestyle='-', label='robot direction')
    

    # Create a color map
     colors = plt.cm.viridis(np.linspace(0, 1, len(set([obj['object_type'] for obj in objects]))))
     color_map = {obj_type: colors[i] for i, obj_type in enumerate(set([obj['object_type'] for obj in objects]))}

    

     object_patches = []
     object_labels = []

    

     for obj in objects:
        obj_poly = obj['geometry']['ids']
        obj_coords = [points2d[id] for id in obj_poly[0]]
        obj_color = color_map[obj['object_type']]
        obj_patch = mpatches.Polygon(obj_coords, facecolor=obj_color, edgecolor='black')
        ax.add_patch(obj_patch)
        object_patches.append(obj_patch)
        object_labels.append(obj['object_type'])

     #object_legend = [mlines.Line2D([0], [0], color=color_map[l], lw=4, label=f"{l} ({color_map[l]})") for l in object_labels]
     object_legend = [mlines.Line2D([0], [0], color=color_map[l], lw=4, label=f"{l} ") for l in object_labels]


     if hazards_data:
         for  hazard_layer in hazards_data:
              if hazard_layer['layer_type'] == 'hazards':
                  for hazard in hazard_layer['list']:
                      hazard_coords = hazard['geometry']['coordinates'][0]
                      hazard_polygon = patches.Polygon(hazard_coords, fill=True, color='red', alpha=0.5, label='Hazard')
                      ax.add_patch(hazard_polygon)
    
    
                          
    #  if escape_events_data:
    #     for event_data in escape_events_data['geometry']['list']:
    #         x, y, ori_rad = event_data['pose']
    #         event_type = event_data['event']
            
    #         # Choose marker color based on event type
    #         if event_type == "brush_stall_detected":
    #             color = 'cyan'
    #         elif event_type == "wheel_dropped":
    #             color = 'purple'
    #         else:
    #             color = 'gray'  # default color for unknown events
                
    #         ax.plot(x, y, 'o', color=color, label=event_type)

                  
             


     #object_legend = [mlines.Line2D([0], [0], color='grey', lw=4, label=l) for l in object_labels]

     handles=[arrow_legend,start_dot,end_dot,door_legend]
     if doc_dot is not None:
         handles.append(doc_dot)
    
     if hazards_data:
        hazard_legend = mpatches.Patch(color='red', alpha=0.5, label='Hazard')
        handles.append(hazard_legend)
    
       # Add escape events legend if escape_events_data is provided
    #  if escape_events_data:
    #     brush_stall_legend = mpatches.Patch(color='cyan', label='Brush Stall Detected')
    #     wheel_dropped_legend = mpatches.Patch(color='purple', label='Wheel Dropped')
    #     handles.extend([brush_stall_legend, wheel_dropped_legend])

     handles.extend(object_legend)

     legend=plt.legend(handles=handles, bbox_to_anchor=(1, 1), loc='upper right', fontsize='x-small',ncol=2)
     legend.get_frame().set_alpha(0.5)
     ax.set_aspect('equal', adjustable='datalim')
     buf = io.BytesIO()
     canvas = FigureCanvas(fig)
     canvas.print_png(buf)
     plt.close(fig)  # Close the figure to free up memory
     buf.seek(0)
     return buf



def download_json(url, save_as):
    response = requests.get(url)
    
    # Ensure we got a successful response
    if response.status_code == 200:
        with open(save_as, 'w') as file:
            file.write(response.text)
    else:
        print(f"Failed to retrieve content from {url}. Status code: {response.status_code}")   


def search_mission(nMssion, r_json):
    with open('r.json') as f:
        data =json.load(f)

    
app = Flask(__name__)
app.secret_key = 'this-is-a-secret-key'


@app.route('/mission_details',methods=['POST'])
def mission_details():
    docked_at_start = None
    data = request.get_json()
    mission_number = int(data.get('mission_id')) 
    #print("printMisionId==>",mission_number)
    with open('r.json') as f:
        data_content  =json.load(f)

    #filtered_data = [(entry['dockedAtStart'], entry['missionId']) for entry in data_content if entry.get('nMssn') == mission_number]
    filtered_data = [entry for entry in data_content if entry.get('nMssn') == mission_number]
    # for entry in filtered_data:
    #   print(json.dumps(entry, indent=4)) 
    # for docked, mission_id in filtered_data:
    #  print(f"Docked At Start: {docked}, Mission ID: {mission_id}")
    first_dict = filtered_data[0]
    doneM = first_dict.get('doneM',None) #Total duration in minutes the Roomba has run for all missions.
    saves = first_dict.get('saves',None)
    softwareVer = first_dict.get('softwareVer',None) #Software version installed on Roomba.
    dockedAtStart = first_dict.get('dockedAtStart', None) # Boolean indicating if Roomba was docked at start of mission.
    chrgs = first_dict.get('chrgM',None)# No. of time charged during mission
    pauseM = first_dict.get('pauseM',None)
    durationM = first_dict.get('durationM',None)
    done_raw_value = first_dict.get('done_raw', None) #Roomba got back to Dock after the mission
    start_time = first_dict.get('startTime', None) # Start timestamp for mission.
    #start_time = datetime.utcfromtimestamp(start_time) # real time
    start_time = datetime.datetime.utcfromtimestamp(start_time)
    start_time = start_time - datetime.timedelta(hours=5)

    initiator =  first_dict.get('initiator', None) #how roomba started
    done = first_dict.get('done',None) # Completion status.
    eDock = first_dict.get('eDock',None) #Ending dock state
    sqft = first_dict.get('sqft',None) #Estimated area cleaned during mission.
    evacs = first_dict.get('evacs',None) #Number of bin full events during mission.
    end_time = first_dict.get('timestamp',None) # End time of the mission
    #end_time =  datetime.utcfromtimestamp(end_time)
    end_time = datetime.datetime.utcfromtimestamp(end_time)
    end_time = end_time - datetime.timedelta(hours=5)
    runM = first_dict.get('runM',None) #total Running time
    dirt = first_dict.get('dirt',None)

#  "pmaps": [
#             {
#                 "AauwnpndS8-JUHG_4o19_Q": "230818T231204"
#             }
#         ],


    # pmap_id = first_dict['pmaps_info'][0]['pmap_id']
    # pmapv_id = first_dict['pmaps_info'][0]['pmapv_id']

    pmap_id = list(first_dict['pmaps'][0].keys())[0]
    pmapv_id = first_dict['pmaps'][0][pmap_id]

    robot_id = first_dict.get('robot_id',None)
    # print("pmap_id_from_map",pmap_id)
    # print("pmapv_id_from_map",pmapv_id)

    odoaFeats_data = first_dict.get('odoaFeats', {})
    extracted_data = {}
    for attribute, value in odoaFeats_data.items():
       extracted_data[attribute] = value
   
    return jsonify({"extracted_data": extracted_data,"doneM":doneM,"saves":saves,"softwareVer":softwareVer,"dockedAtStart":dockedAtStart,
                    "done_raw_value":done_raw_value,"start_time":start_time,"initiator":initiator,"done":done,"eDock":eDock,
                    "sqft":sqft,"evacs":evacs,"end_time":end_time,"runM":runM,"chrgs":chrgs,"dirt":dirt,"pauseM":pauseM,"durationM":durationM,
                    "pmap_id":pmap_id,"pmapv":pmapv_id,"robotId":robot_id
                    })

   
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    session['username'] = username
    session['password'] = password
    irobot_auth = IrobotAuthorization(username, password)
    irobot_auth.login()
    robotDetails = irobot_auth.get_details()
    robot_id = list(robotDetails.keys())[0]
    robot_info = robotDetails[robot_id]
    robot_password = robot_info['password'] 
    sku = robot_info['sku']
    user_cert = robot_info['user_cert']
    soft_version = robot_info['softwareVer']
    robot_name = robot_info['name']
    # Store the irobot_auth instance in the session or a global variable, so that it can be accessed later in other routes
    session['logged_in'] = True
    return jsonify({"status": "success"})

@app.route('/map_json', methods=['GET'])
def map_json():
    with open('map.json', 'r') as f:
        map_data = json.load(f)
    return jsonify(map_data)

@app.route('/maps', methods=['GET'])
def g_maps():

 # Check if the user is logged in
    if not session.get('logged_in'):
        return jsonify({"error": "Not logged in"})
   # Retrieve the username and password from the session
    username = session.get('username')
    password = session.get('password')
    irobot_auth = IrobotAuthorization(username, password)
    irobot_auth.login()
    robotID = irobot_auth.get_credentials()
    #print("robotId==>",robotID)
    pmaps = irobot_auth.get_maps(robotID)
    #print("pmaps===>",pmaps)
    #return jsonify({"robotID": robotID, "pmaps": pmaps})
    result = []
    # If there's only one map, print it
    if len(pmaps) == 1:
        result.append({"robot_id": robotID, "map": pmaps[0]})
    else:
        # Enumerate all maps
        for i, map in enumerate(pmaps):
            result.append({"robot_id": robotID, "map_number": i+1, "map": map})
    return jsonify(result)



@app.route('/all_maps', methods=['GET'])
def all_maps():

    # Check if the user is logged in
    if not session.get('logged_in'):
        return jsonify({"error": "Not logged in"})
    # Retrieve the username and password from the session
    username = session.get('username')
    password = session.get('password')
    # Create a new irobot_auth instance
    irobot_auth = IrobotAuthorization(username, password)
    irobot_auth.login()
    # Get the robot ID
    robotID = irobot_auth.get_credentials()
    # Get the maps related to this robot
    robot_maps = irobot_auth.get_maps(robotID)
    # Prepare a result list
    result = []
    # If there's only one map, print it
    if len(robot_maps) == 1:
        result.append({"robot_id": robotID, "map": robot_maps[0]})
    else:
        # Enumerate all maps
        for i, map in enumerate(robot_maps):
            result.append({"robot_id": robotID, "map_number": i+1, "map": map})
    return jsonify(result)



@app.route('/view_map/<robotID>/<pmapID>/<pmapv>', methods=['GET'])
def view_map(robotID, pmapID,pmapv):
    # Retrieve the irobot_auth instance from the session or global variable
    # Check if the user is logged in
    if not session.get('logged_in'):
        return jsonify({"error": "Not logged in"})
    # Retrieve the username and password from the session
    username = session.get('username')
    password = session.get('password')
    # Create a new irobot_auth instance
    irobot_auth = IrobotAuthorization(username, password)
    irobot_auth.login()

    map_data = irobot_auth.view_maps(robotID, pmapID,pmapv)
    mission_map_data = json.dumps(map_data)

    save_as = 'mission_map.txt'
    with open(save_as, 'w') as file:
        file.write(mission_map_data)

    print('map_data==>',map_data)
    


    points2d = {}
    for point in map_data['maps'][0]['points2d']:
      id_ = int(point['id'])
      coordinates = point['coordinates']
      points2d[id_] = coordinates

    borders = []
    for border in map_data['maps'][0]['borders']:
     ids = [[int(id_) for id_ in region] for region in border['geometry']['ids']]
     new_border = {
        "free_type": border["free_type"],
        "geometry": {
            "ids": ids,
            "type": border["geometry"]["type"] 
        },
        "id": border["id"]
    }
     borders.append(new_border)

    poses2d = []
    for pose in map_data['maps'][0]['poses2d']:
        new_pose = {
            "coordinates": pose["coordinates"],
            "id": int(pose["id"]), 
            "ori_rad": pose["ori_rad"]
        }
        poses2d.append(new_pose)

    print("poses2d",poses2d)

    typed_poses = {}
    for pose_type, pose in map_data['maps'][0]['typed_poses'].items():
        new_pose = {
            "geometry": {
                "ids": [int(id_) for id_ in pose["geometry"]["ids"]],
                "type": pose["geometry"]["type"]
            }
        } 
        typed_poses[pose_type] = new_pose
    
    #print("typed_pose",typed_poses)

    objects = []
    for obj in map_data['maps'][0]['objects']:
        ids = [[int(id_) for id_ in geometry] for geometry in obj['geometry']['ids']]
        new_obj = {
            "id": obj["id"],
            "region_id": obj["region_id"],
            "object_type": obj["object_type"],
            "geometry": {
                "ids": ids,
                "type": obj["geometry"]["type"]
            },
            "front_pose": obj["front_pose"],
            "image_resource_id": obj["image_resource_id"],
            "system": obj["system"],
            "user": obj["user"],
            "features": obj["features"]
        }  
        objects.append(new_obj)
    #print("objects==>",objects)


    hazards_data = [layer for layer in map_data['maps'][0]["layers"] if layer["layer_type"] == "hazards"]
    escape_events = [layer for layer in map_data['maps'][0]["layers"] if layer["layer_type"] == "escape_events"]
    print("escape_events====>>>",escape_events)


    region_suggestions = [
        {
            "region_id":"1", 
            "suggested_types":[
            {"region_type":"office", "score":1.7631},
            {"region_type":"living_room", "score":0.1518}
            ]
        }
    ]

    regions = []
    for region in map_data['maps'][0]['regions']:
        ids = [int(id_) for id_ in region['geometry']['ids'][0]]

        new_region = {
        "id": region["id"],
        "geometry": {
        "ids": ids,
        "type": region["geometry"]["type"]
        },
        "features": region["features"], 
        "name": region["name"],
        "region_type": region["region_type"],
        "policies": region["policies"]
        }
        for suggestion in region_suggestions:
    
         if region['id'] == suggestion['region_id']:
            suggested_types = suggestion['suggested_types']
            suggested_types.sort(key=lambda x: x['score'], reverse=True)
            top_suggestion = suggested_types[0]
            region['region_type'] = top_suggestion['region_type']

        regions.append(new_region)
    #print("Updated Regions:")
  

    doors = []
    for door in map_data['maps'][0]['doors']:
     door_coords = [points2d[int(id_)] for id_ in door['geometry']['ids']]
     doors.append(door_coords)
    
    print("doors---->",doors)

   

    img = plot_map(points2d, borders, poses2d,typed_poses,objects,doors,hazards_data)
   
    return send_file(img, mimetype='image/png')
  



@app.route('/view_map_brief/<robotID>/<pmapID>/<pmapv>', methods=['GET'])
def view_map_brief(robotID, pmapID,pmapv):
    # Check if the user is logged in
    if not session.get('logged_in'):
        return jsonify({"error": "Not logged in"})

    # Retrieve the username and password from the session
    username = session.get('username')
    password = session.get('password')

    # Create a new irobot_auth instance
    irobot_auth = IrobotAuthorization(username, password)
    irobot_auth.login()

    id = None
    version = None
    map_name = None
    create_time = None
    learning_percentage = None
    resolution = None
    user_orientation_rad = None
    robot_orientation_rad = None
    area = None
    nmssn = None
    mission_id = None

    # Get the map data
    map_data = irobot_auth.view_maps(robotID, pmapID,pmapv)
    map_data_str = json.dumps(map_data)

    #print("distinct_map_details===>",map_data_str)
    save_as = 'map_info.txt'
    with open(save_as, 'w') as file:
        file.write(map_data_str)
    

    #print(json.dumps(map_data, indent=4))
    id = map_data['maps'][0]['map_header']['id']
    version = map_data['maps'][0]['map_header']['version']
    map_name = map_data['maps'][0]['map_header']['name']
    create_time = map_data['maps'][0]['map_header']['create_time']
    create_time = datetime.datetime.fromtimestamp(create_time)
    learning_percentage = map_data['maps'][0]['map_header']['learning_percentage']
    resolution = map_data['maps'][0]['map_header']['resolution']
    user_orientation_rad = map_data['maps'][0]['map_header']['user_orientation_rad']
    robot_orientation_rad = map_data['maps'][0]['map_header']['robot_orientation_rad']
    area = map_data['maps'][0]['map_header']['area']
    #version = map_data['maps'][0]['map_header']['version']
    try:
     nmssn = map_data['maps'][0]['map_header']['nmssn']
    except (KeyError, IndexError, TypeError):
     nmssn = None
    try:
     mission_id = map_data['maps'][0]['map_header']['mission_id']
    except (KeyError, IndexError, TypeError):
     mission_id = None

   
    return jsonify({"id":id,"version":version,"map_name": map_name, "create_time": create_time,"learning_percentage":learning_percentage
                    ,"resolution": resolution,"user_orientation_rad":user_orientation_rad,"robot_orientation_rad":robot_orientation_rad,
                    "area":area,"version":version,"nmssn":nmssn,"mission_id":mission_id})

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/info', methods=['GET'])
def info():

     if not session.get('logged_in'):
      return jsonify({"error": "Not logged in"})

# Retrieve the username and password from the session
     username = session.get('username')
     password = session.get('password')

    # Create a new irobot_auth instance
     irobot_auth = IrobotAuthorization(username, password)
     irobot_auth.login()

     robotDetails = irobot_auth.get_details()
     robot_id = list(robotDetails.keys())[0]
     robot_info = robotDetails[robot_id]
     robot_password = robot_info['password'] 
     sku = robot_info['sku']
     user_cert = robot_info['user_cert']
     soft_version = robot_info['softwareVer']
     robot_name = robot_info['name']
     return jsonify({"robot_id": robot_id,"robot_password":robot_password,"sku":sku,"user_cert":user_cert,"soft_version":soft_version,"robot_name":robot_name})



@app.route('/time_estimation', methods=['GET'])
def time_estimation():

     if not session.get('logged_in'):
      return jsonify({"error": "Not logged in"})

# Retrieve the username and password from the session
     username = session.get('username')
     password = session.get('password')

    # Create a new irobot_auth instance
     irobot_auth = IrobotAuthorization(username, password)
     irobot_auth.login()

     robotDetails = irobot_auth.get_details()
     robot_id = list(robotDetails.keys())[0]

     time_estimation = irobot_auth.time_estimation(robot_id)
     #print("time_estimation==>",time_estimation)
     
     return jsonify(time_estimation)




@app.route('/mission_history', methods=['GET'])
def mission_history():
    if not session.get('logged_in'):
      return jsonify({"error": "Not logged in"})

# Retrieve the username and password from the session
    username = session.get('username')
    password = session.get('password')

    # Create a new irobot_auth instance
    irobot_auth = IrobotAuthorization(username, password)
    irobot_auth.login()

    robotDetails = irobot_auth.get_details()
    robot_id = list(robotDetails.keys())[0]
    mission_history = irobot_auth.view_mission_history(robot_id)
    mission_ids  =[]
    for m in mission_history:
        mission_id = m['missionId']
        mission_num =m['nMssn']
        mission_timestamp = m['timestamp']
        mission_time = datetime.datetime.utcfromtimestamp(mission_timestamp)
        mission_time = mission_time - datetime.timedelta(hours=5)
        cmd = m['cmd']
        mission_start_time = cmd['time']
        # print("mission_Start_time",mission_start_time)
        mission_start_time = datetime.datetime.utcfromtimestamp(mission_start_time)
        mission_start_time = mission_start_time - datetime.timedelta(hours=5)

        mission_ids.append((mission_num,mission_id,mission_start_time))

    # with open('r.json') as f:
    #   data = json.load(f)

    # total_duration = 0
    # total_area = 0
    # for item in data:
    #  total_duration += item['durationM']
    #  #total_area += item['area']
    # print("total_duration===>",total_duration)
  

    
    
    # print("missionId===>",mission_ids)

    return jsonify({"mission_id": mission_ids})
    # with open('mission_history.json', 'w') as f:
    #    json.dump(mission_history, f)
    #return plot_missionHistory(mission_history)
    # return jsonify(mission_history), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
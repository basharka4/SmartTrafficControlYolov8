from ultralytics import YOLO
import cv2
import time
import numpy as np
import serial
import serial.tools.list_ports

# تحميل نموذج YOLOv8
model = YOLO("yolov8n.pt")

# تهيئة الكاميرا
cap = cv2.VideoCapture(0)
polygon_points = []
selected_zones = []
first_point = None
second_point = None
current_mouse_position = None

# تعريف مناطق التقاطع
frame_width, frame_height = 640, 480
center = (frame_width // 2, frame_height // 2)

quadrants = {
    "north": (0, 0, center[0], center[1]),
    "east": (center[0], 0, frame_width, center[1]),
    "south": (center[0], center[1], frame_width, frame_height),
    "west": (0, center[1], center[0], frame_height)
}

ardiuno_light_pins ={
    "north" : (2 , 3 , 4),
    "east" : (5 , 6 , 7),
    "south" : (8 , 9 , 10),
    "west" : (11 , 12 , 13)
}

# تعريف إشارات المرور
light_positions = {
    "north": (center[0] - 50, 20),
    "east": (frame_width - 70, center[1] - 50),
    "south": (center[0] - 50, frame_height - 120),
    "west": (20, center[1] - 50)
}

# حالة الإشارات
light_states = {"north": "red", "east": "red", "south": "red", "west": "red"}
light_sequence = ["north", "east", "south", "west"]
recently_active = []
select_zones = True

# فتح سيريال
# ser = serial.Serial('COM8', 9600, timeout=1)
ser =  None
time.sleep(2)

# إعدادات التوقيت
MIN_GREEN_DURATION = 5
MAX_GREEN_DURATION = 20
YELLOW_DURATION = 3  # 3 ثواني للإشارة الصفراء
last_switch_time = time.time()
current_green_light = None
next_green_light = light_sequence[0]
yellow_start_time = None  # وقت بداية الإشارة الصفراء
current_green_duration=0

def connect_arduino():
        global ser
        ports = serial.tools.list_ports.comports()
        for port in ports:
            try:
                ser = serial.Serial(port.device, 9600, timeout=1)
                time.sleep(2)  # انتظار الاتصال
                print(f"Connected To : {port.device}")
                return
            except:
                pass
        print("No Arduino Connected...!!")
    

def send_command(command):
    global ser
    ser.write(f'{command}\n'.encode('utf-8'))
    print(command)


def clean_light():
    global light_states , ardiuno_light_pins
    for zone, light_state in light_states.items():
        pins = ardiuno_light_pins[zone]
        send_command(f'L{pins[0]}') 
        send_command(f'L{pins[1]}') 
        send_command(f'L{pins[2]}') 


def update_arduino_light_mode():
    global light_states , ardiuno_light_pins
    for zone, light_state in light_states.items():
        pins = ardiuno_light_pins[zone]
        if light_state == "red":
            send_command(f'H{pins[0]}') 
            send_command(f'L{pins[1]}') 
            send_command(f'L{pins[2]}') 
        elif light_state == "yellow":
            send_command(f'L{pins[0]}') 
            send_command(f'H{pins[1]}') 
            send_command(f'L{pins[2]}') 
        elif light_state == "green":
            send_command(f'L{pins[0]}') 
            send_command(f'L{pins[1]}') 
            send_command(f'H{pins[2]}')


def confirm():
    global select_zones , quadrants , light_positions , light_states , light_sequence , next_green_light , ardiuno_light_pins
    if len(selected_zones) > 0 and len(selected_zones) < 5 :
        new_quadrants = {}
        new_light_positions = {}
        new_light_states = {}
        new_light_sequence = []
        new_ardiuno_light_pins = {}
        for index , selected_zone in enumerate(selected_zones):
            new_quadrants["zone" + str(index)] = (selected_zone[0][0] ,selected_zone[0][1] ,selected_zone[1][0] ,selected_zone[1][1])
            new_light_positions["zone" + str(index)] = (selected_zone[0][0] ,selected_zone[1][1] - 100 )
            new_light_states["zone" + str(index)] = "red"
            new_light_sequence.append("zone" + str(index))
            new_ardiuno_light_pins["zone" + str(index)] = ( index * 3 + 2  , index* 3 + 3 , index * 3 + 4 )
        print(new_quadrants)
        print(new_light_positions)
        print(new_light_states)
        print(new_light_sequence)
        print(new_ardiuno_light_pins)
        quadrants = new_quadrants
        light_sequence = new_light_positions
        light_positions = new_light_positions
        light_states = new_light_states
        ardiuno_light_pins = new_ardiuno_light_pins
        next_green_light = new_light_sequence[0]
    select_zones=False
    

def draw_lights(frame):
    for zone, pos in light_positions.items():
        # رسم مربع الإشارة
        cv2.rectangle(frame, pos, (pos[0] + 40, pos[1] + 100), (0, 0, 0), -1)
        
        # ألوان الإشارة
        color_red = (0, 0, 255) if light_states[zone] == "red" else (40, 40, 40)
        color_yellow = (0, 255, 255) if light_states[zone] == "yellow" else (40, 40, 40)
        color_green = (0, 255, 0) if light_states[zone] == "green" else (40, 40, 40)
        
        # رسم ألوان الإشارة
        cv2.circle(frame, (pos[0] + 20, pos[1] + 20), 10, color_red, -1)
        cv2.circle(frame, (pos[0] + 20, pos[1] + 50), 10, color_yellow, -1)
        cv2.circle(frame, (pos[0] + 20, pos[1] + 80), 10, color_green, -1)

        # اسم المنطقة
        cv2.putText(frame, zone, (pos[0], pos[1] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def calculate_green_duration(count):
    return min(MAX_GREEN_DURATION, max(MIN_GREEN_DURATION, count * 2 + MIN_GREEN_DURATION))


def update_traffic_lights(counts):
    global last_switch_time, light_states, current_green_light, next_green_light, yellow_start_time , current_green_duration , light_sequence

    current_time = time.time()
    elapsed_time = current_time - last_switch_time

    # إذا لم يكن هناك إشارة خضراء نشطة
    if current_green_light is None:
        light_states[next_green_light] = "green"
        current_green_light = next_green_light
        last_switch_time = current_time
        yellow_start_time = None
        return

    # إذا كانت الإشارة الحالية خضراء
    if light_states[current_green_light] == "green":
        if current_green_duration == 0:
            current_green_duration = calculate_green_duration(counts.get(current_green_light, 0))
        if elapsed_time > current_green_duration:
            current_green_duration = 0
            light_states[current_green_light] = "yellow"
            last_switch_time = current_time
            yellow_start_time = current_time  # تسجيل وقت بداية الإشارة الصفراء

    # إذا كانت الإشارة الحالية صفراء
    elif light_states[current_green_light] == "yellow" and yellow_start_time is not None:
        yellow_elapsed = current_time - yellow_start_time
        
        if yellow_elapsed > YELLOW_DURATION:
            # إيقاف الإشارة الحالية
            light_states[current_green_light] = "red"
            recently_active.append(current_green_light)
            if len(recently_active) > int(len(light_sequence)/2):
                recently_active.pop(0)

            # تحديد الإشارة التالية (المنطقة الأكثر ازدحامًا)
            next_green_light = max(counts, key=counts.get, default="zone0")
            
            # إذا كانت جميع المناطق فارغة، ننتقل بالتتابع
            if all(count == 0 for count in counts.values()) or next_green_light in recently_active:
                zones = list(quadrants.keys())
                current_index = zones.index(current_green_light)
                next_green_light = zones[(current_index + 1) % len(zones)]
            
            # تشغيل الإشارة الجديدة
            # if next_green_light in recently_active:
            #     zones = list(quadrants.keys())
            #     current_index = zones.index(current_green_light)
            #     next_green_light = zones[(current_index + 1) % len(zones)]
            light_states[next_green_light] = "green"
            current_green_light = next_green_light
            last_switch_time = current_time
            yellow_start_time = None


def mouse_callback(event, x, y, flags, param):
    global current_mouse_position , first_point , second_point
    if event == cv2.EVENT_MOUSEMOVE:
        current_mouse_position = (x,y)
    if event == cv2.EVENT_LBUTTONDOWN:
        if not first_point:
            first_point = (x,y)
        else:
            selected_zones.append((first_point , (x,y)))
            first_point = None

    if event == cv2.EVENT_RBUTTONDOWN:
        first_point = None
        # polygon_points.append((x, y))
        print(f"Point Added: (X: {x}, Y: {y})")


connect_arduino()

while True:

    ret, frame = cap.read()
    
    if not ret:
        print("Failed to read frame from camera...!")
        break

    frame = cv2.resize(frame, (frame_width, frame_height))
    if select_zones :
        cv2.namedWindow('Frame')
        color = (0, 255, 0) 

        cv2.setMouseCallback('Frame', mouse_callback)
        if len(selected_zones) > 0:
            for selected_zone in selected_zones:
                cv2.rectangle(frame, selected_zone[0], selected_zone[1], color, 2)
        if first_point :
            cv2.rectangle(frame, first_point, current_mouse_position, color, 2)

        cv2.imshow('Frame', frame)
        if cv2.waitKey(1) == ord('q'):
            break
        if cv2.waitKey(1) == ord('s'):
            confirm()
    else:    
        # الكشف عن المركبات
        results = model(frame)
        counts = {zone: 0 for zone in quadrants}
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                if int(box.cls[0]) in [2, 5, 7]:  # سيارات، حافلات، شاحنات
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    for zone, (x_start, y_start, x_end, y_end) in quadrants.items():
                        if x_start <= cx < x_end and y_start <= cy < y_end:
                            counts[zone] += 1
                            break

        # تحديث إشارات المرور
        update_traffic_lights(counts)

        if ser:
            update_arduino_light_mode()

        # رسم المناطق
        for zone, (x_start, y_start, x_end, y_end) in quadrants.items():
            color = (0, 255, 0) if light_states[zone] == "green" else (0, 0, 255)
            cv2.rectangle(frame, (x_start, y_start), (x_end, y_end), color, 2)

        # رسم إشارات المرور
        draw_lights(frame)

        # عرض عدد المركبات
        for i, (zone, count) in enumerate(counts.items()):
            cv2.putText(frame, f"{zone}: {count}", (10, 30 + i * 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # عرض الوقت المتبقي
        if current_green_light:
            if light_states[current_green_light] == "green":
                # current_green_duration = calculate_green_duration(counts.get(current_green_light, 0))
                remaining_time = max(0, current_green_duration - (time.time() - last_switch_time))
                cv2.putText(frame, f"Green: {int(remaining_time)}s", (frame_width - 200, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            elif light_states[current_green_light] == "yellow" and yellow_start_time is not None:
                yellow_remaining = max(0, YELLOW_DURATION - (time.time() - yellow_start_time))
                cv2.putText(frame, f"Yellow: {int(yellow_remaining)}s", (frame_width - 200, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow('Traffic Control', frame)
        if cv2.waitKey(1) == ord('q'):
            break


cap.release()
cv2.destroyAllWindows()

if ser:
    clean_light()
    ser.close()